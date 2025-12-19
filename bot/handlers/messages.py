from aiogram import Router
from aiogram.types import Message

from services.llm import LLMServiceError, llm_service

router = Router(name="messages")

@router.message()
async def llm_handler(message: Message) -> None:
    if message.bot:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )
    try:
        output=await llm_service.ask(message.text)
        await message.answer(text=output)
    except LLMServiceError as e:
        await message.answer(e.user_message)