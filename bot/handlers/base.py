from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="base")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """ /start command handler
    
    """
    await message.answer(
        text=(
            "<b>Привет, меня зовут Statistico :)</b>\n\n"
            "Я могу отвечать на твои вопросы на естественном русском языке в стиле:\n"
            "- Сколько всего видео есть в системе?\n"
            "- Сколько видео у креатора с id X вышло с 1 ноября 2025 по 5 ноября 2025 включительно?\n"
            "- Сколько видео набрало больше 100 000 просмотров за всё время?\n"
            "- На сколько просмотров в сумме выросли все видео 28 ноября 2025?\n\n"
            "Ты мне вопрос а я тебе число, Поехали!"
        )
    )

@router.message()
async def echo_handler(message: Message) -> None:
    """ /start command handler
    
    """
    await message.answer(text=message.text)