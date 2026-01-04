import functools
import json
import logging
from collections.abc import Callable
from json import JSONDecodeError
from typing import ParamSpec, TypeVar

from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)

from bot.config import settings
from services.exceptions import LLMServiceError

T = TypeVar('T')
P = ParamSpec('P')

logger = logging.getLogger(__name__)

def handle_llm_errors(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to handle OpenAI API errors and convert to LLMServiceError"""

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await func(*args, **kwargs)

        except (AuthenticationError, PermissionDeniedError) as e:
            raise LLMServiceError(
                message=str(e),
                user_message="🔒 Проблема авторизации LLM. Обратитесь к администратору."
            ) from e

        except RateLimitError as e:
            raise LLMServiceError(
                message=str(e),
                user_message="⏱ LLM временно недоступен. Превышен лимит запросов."
            ) from e

        except (BadRequestError, UnprocessableEntityError) as e:
            raise LLMServiceError(
                message=str(e),
                user_message="⚠️ Некорректный запрос к LLM."
            ) from e

        except NotFoundError as e:
            raise LLMServiceError(
                message=str(e),
                user_message="🔍 Модель LLM не найдена."
            ) from e

        except InternalServerError as e:  # явно ловим 500+
            raise LLMServiceError(
                message=str(e),
                user_message="🔧 Внутренняя ошибка LLM."
            ) from e

        except APIConnectionError as e:
            raise LLMServiceError(
                message=str(e),
                user_message="🌐 Сетевая ошибка при обращении к LLM."
            ) from e

        except APIError as e:
            raise LLMServiceError(
                message=str(e),
                user_message="❌ Ошибка API LLM."
            ) from e

        except Exception as e:
            raise LLMServiceError(
                message=str(e),
                user_message="💥 Неожиданная ошибка LLM."
            ) from e

    return wrapper

class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_BASE_URL,
            timeout=20.0,
            max_retries=2,
        )
        self._model = settings.GEMINI_MODEL

    @handle_llm_errors
    async def ask(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        messages: list[dict[str, str]] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        logger.debug(f"Calling LLM without tools: model={self._model}, temp={temperature}")
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.debug(f"LLM response received: {len(response.choices)}")

        return response.choices[0].message.content

    @handle_llm_errors
    async def ask_with_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> dict:
        messages: list[dict[str, str]] = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Calling LLM with tools: model={self._model}, temp={temperature}")

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_query_intent"}},
        )
        logger.debug(f"LLM response received: {len(response.choices)} choices")

        choice = response.choices[0].message

        if not choice.tool_calls:
            raise LLMServiceError(
                message="No tool calls in response",
                user_message="LLM не вернул структурированный ответ"
            )
        tool_call = choice.tool_calls[0]

        if tool_call.function.name != "extract_query_intent":
            raise LLMServiceError(
                message=f"Unexpected function: {tool_call.function.name}",
                user_message="LLM вернул неожиданную функцию"
            )

        try:
            data = json.loads(tool_call.function.arguments)
            return data
        except JSONDecodeError as e:
            raise LLMServiceError(
                message=f"Invalid JSON: {e}",
                user_message="LLM вернул некорректный JSON"
            ) from e

llm_service = LLMService()