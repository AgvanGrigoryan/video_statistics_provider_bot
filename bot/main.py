import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.handlers.base import router as base_router
from bot.handlers.messages import router as messages_router
from bot.logging import setup_logging

setup_logging(settings.LOG_LEVEL, use_colors=True)

logger = logging.getLogger(__name__)

async def main() -> None:

    bot = Bot(
        token=settings.TG_BOT_SECRET_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp = Dispatcher()

    dp.include_router(base_router)
    dp.include_router(messages_router)
    
    logger.info("Starting bot...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)

        await dp.start_polling(bot)    
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")