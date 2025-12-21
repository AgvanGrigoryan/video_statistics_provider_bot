import logging

from aiogram import Router
from aiogram.types import Message

from database.engine import get_async_session
from services.analytics_service import AnalyticsError, analytics_service
from services.llm import LLMServiceError
from services.nlp.exceptions import NLPParseError

router = Router(name="messages")

logger = logging.getLogger(__name__)

@router.message()
async def llm_handler(message: Message) -> None:
    if message.bot:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )
    try:
        async for session in get_async_session():
            result = await analytics_service.process_user_query(
                user_message=message.text,
                session=session,
            )
        await message.answer(text=str(result))
    except LLMServiceError as e:
        await message.answer(e.user_message)
    except NLPParseError as e:
        await message.answer(f"{e}.\n Попробуйте переформулировать запрос.")
    except AnalyticsError as e:
        await message.answer(f"<b>Ошибка БД</b>\n\n{e.user_message}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        await message.answer("❌ Внутренняя ошибка бота")