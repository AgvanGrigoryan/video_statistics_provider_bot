import logging

from aiogram import Router
from aiogram.types import Message

from database.engine import get_async_session
from services.analytics_service import analytics_service
from services.exceptions import ServiceError

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
                user_id=message.from_user.id,
            )
        await message.answer(text=str(result))
    except ServiceError as e:
        await message.answer(f"❌ {e.user_message}")
    except Exception as e:
        logger.exception(f"Unhandled error in handler: {e}")
        await message.answer("💥 Произошла критическая ошибка. Попробуйте позже.")