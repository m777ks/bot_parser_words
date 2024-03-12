from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def buttons_words_group(session_name):
    button_words = InlineKeyboardButton(
                text='Слова',
                callback_data=f'button_words_{session_name}'
            )
    button_groups = InlineKeyboardButton(
                text='Группы',
                callback_data=f'button_groups_{session_name}'
            )
    button_cancel = InlineKeyboardButton(
                text='Мои сессии',
                callback_data='/my_sessions'
            )
    markup = InlineKeyboardMarkup(inline_keyboard=[[button_words, button_groups], [button_cancel]])
    return markup


def button_list_words(session_name):
    button_key = InlineKeyboardButton(
        text='Редактировать ключи',
        callback_data=f'edit_words_0_{session_name}'
    )
    button_exception = InlineKeyboardButton(
        text='Редактировать исключения',
        callback_data=f'edit_words_1_{session_name}'
    )
    button_back = InlineKeyboardButton(
        text='Назад',
        callback_data=f'button_back_{session_name}'
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[button_key], [button_exception], [button_back]])
    return markup

