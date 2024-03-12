import sqlite3

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON


def create_list_keyboard(*args: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in sorted(filter(None, args)):
        kb_builder.row(InlineKeyboardButton(
            text=f'{button}',
            callback_data=f'session_name_{str(button)}'
        ))
    # Добавляем в клавиатуру в конце две кнопки "Редактировать" и "Отменить"
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['edit_bookmarks_button'],
            callback_data='edit_sessions'
        ),
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        ),
        width=2
    )
    return kb_builder.as_markup()


def create_edit_keyboard(*args: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in sorted(filter(None, args)):
        kb_builder.row(InlineKeyboardButton(
            text=f'{LEXICON["del"]} {button}',
            callback_data=f'{button}_delete'
        ))

    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        )
    )

    return kb_builder.as_markup()


def create_list_group(*args: str, session_name: str) ->InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in sorted(filter(None, args)):
        kb_builder.row(InlineKeyboardButton(
            text=f'{button}',
            callback_data=f'{button}'
        ))
    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['edit_bookmarks_button'],
            callback_data=f'edit_groups_{session_name}'
        ),
        InlineKeyboardButton(
            text='Добавить',
            callback_data=f'button_add_g_{session_name}'
        ),
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        ),
        width=2
    )
    return kb_builder.as_markup()


def create_edit_keyboard_groups(*args: str, session_name: str) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for button in sorted(filter(None, args)):
        kb_builder.row(InlineKeyboardButton(
            text=f'{LEXICON["del"]} {button}',
            callback_data=f'{button}_delete_gr'
        ))

    kb_builder.row(
        InlineKeyboardButton(
            text=LEXICON['cancel'],
            callback_data='cancel'
        )
    )

    return kb_builder.as_markup()