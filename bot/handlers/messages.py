from aiogram import Router
from aiogram.types import Message

from services.llm import LLMServiceError
from services.nlp.exceptions import NLPParseError
from services.nlp.service import nlp_service

router = Router(name="messages")

@router.message()
async def llm_handler(message: Message) -> None:
    if message.bot:
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )
    try:
        output = await nlp_service.parse_nl(message.text)
        
        await message.answer(text=output.model_dump_json())
    except LLMServiceError as e:
        await message.answer(e.user_message)
    except NLPParseError as e:
        await message.answer(f"{e}.\n Попробуйте переформулировать запрос.")