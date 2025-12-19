import logging

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

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Обёртка для всех ошибок LLM"""
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class LLMService:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_BASE_URL,
            timeout=20.0,
            max_retries=2,
        )
        self._model = settings.GEMINI_MODEL

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

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                # response format is not ready yet
                # response_format={
                #     "type": "json_schema",
                #     "json_schema": {...}
                # }
            )

            return response.choices[0].message.content

        except (AuthenticationError, PermissionDeniedError) as e:
            logger.error(f"LLM auth/permission error: {e}")
            raise LLMServiceError("LLM authentication failed. Contact admin.") from e

        except RateLimitError as e:
            logger.warning(f"LLM rate limit exceeded: {e}")
            raise LLMServiceError("LLM temporarily unavailable due to rate limits.") from e

        except (BadRequestError, UnprocessableEntityError) as e:
            logger.error(f"LLM invalid request: {e}")
            raise LLMServiceError("Invalid request to LLM.") from e

        except NotFoundError as e:
            logger.error(f"LLM model not found: {e}")
            raise LLMServiceError("Requested LLM model not available.") from e

        except InternalServerError as e:  # явно ловим 500+
            logger.error(f"LLM internal server error: {e}")
            raise LLMServiceError("LLM service encountered an internal error.") from e

        except APIConnectionError as e:
            logger.error(f"LLM network error: {e}")
            raise LLMServiceError("LLM service temporarily unavailable. Network issue.") from e

        except APIError as e:
            logger.error(f"LLM API error: {e.status_code} - {e}")
            raise LLMServiceError("LLM service encountered an API error.") from e

        except Exception as e:
            logger.exception(f"Unexpected LLM error: {e}")
            raise LLMServiceError("Unexpected LLM error occurred.") from e

# May be useful
# Using types

# Nested request parameters are TypedDicts. Responses are Pydantic models which also provide helper methods for things like:

#     Serializing back into JSON, model.to_json()
#     Converting to a dictionary, model.to_dict()

# Typed requests and responses provide autocomplete and documentation within your editor. If you would like to see type errors in VS Code to help catch bugs earlier, set python.analysis.typeCheckingMode to basic

llm_service = LLMService()