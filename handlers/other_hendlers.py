from aiogram import Router
from aiogram.types import Message, CallbackQuery

router = Router()

# Этот хэндлер будет реагировать на любые сообщения пользователя,
# не предусмотренные логикой работы бота
@router.message()
async def send_echo(message: Message):
    await message.answer(f'Это эхо! {message.text} \n Топай в /help ')
    print(message.model_dump_json(exclude_none=True, indent=4))


@router.callback_query()
async def send_echo_call(call: CallbackQuery):
    print(call.model_dump_json(exclude_none=True, indent=4))
