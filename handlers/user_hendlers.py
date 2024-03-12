import re
import asyncpg
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from lexicon.lexicon import LEXICON
from utils import functions
from config_data.config import Config, load_config
from keyboards.bookmarks_kb import (create_edit_keyboard, create_list_keyboard,
                                    create_list_group, create_edit_keyboard_groups)
from keyboards.keyboards import buttons_words_group, button_list_words

config: Config = load_config()

router = Router()
create_pool = functions.create_pool()


# Установка соединения с базой данных
async def create_pool():
    return await asyncpg.create_pool(
        user=config.postgres.pguser, password=config.postgres.pgpassword,
        database=config.postgres.database, host=config.postgres.ip)


# Функция для обновления подписки
async def daily_check_subscription(bot: Bot):
    # ваш код проверки и обновления подписки
    await bot.send_message(chat_id=717150843, text='Function subscription')

    pool = await create_pool()
    async with pool.acquire() as conn:
        today = datetime.today()
        await conn.execute('UPDATE users_bot SET access = False WHERE subscriptions_stop < $1', today)
    await pool.close()


class FSMFillForm(StatesGroup):
    register = State()  # Состояние ожидания загрузки email
    waiting_for_session_name = State()  # Устанавливаем состояние ожидания названия сессии
    edit_words = State()  # Состояние "Редактировать ключевые слова"
    edit_words_exceptions = State()  # Состояние "Редактировать слова исключения"
    fill_add_group = State()  # Состояние ожидания добавление группы


# Этот хэндлер будет срабатывать на команду "/start" -
# добавлять пользователя в базу данных, если его там еще не было
# и отправлять ему приветственное сообщение
@router.message(CommandStart(), StateFilter(default_state))
async def process_start_command(message: Message):
    await message.answer(text=LEXICON['/start'])
    print(f'User ID: {message.from_user.id},\n Usename: {message.from_user.username}')


@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()


@router.message(Command(commands='register'), StateFilter(default_state))
async def process_register(message: Message, state: FSMContext):
    pool = await create_pool()
    try:
        await message.delete()
        user_id = message.from_user.id
        async with pool.acquire() as conn:
            # Проверяем, есть ли пользователь в базе
            exists = await conn.fetchval('SELECT EXISTS(SELECT 1 FROM users_bot WHERE user_id = $1)', user_id)
            if not exists:
                await message.answer(text='Пожалуйста, введите ваше email\n\n'
                                          'Если вы хотите прервать регистрацию - '
                                          'отправьте команду\n /cancel')
                await state.set_state(FSMFillForm.register)
            else:
                user_data = await conn.fetchrow(
                    'SELECT email, subscriptions_start, subscriptions_stop, access FROM users_bot WHERE user_id = $1',
                    user_id)
                email, subscriptions_start, subscriptions_stop, access = user_data

                if access:
                    await message.answer(
                        f"Вы зарегистрированы!\nВаш email: {email}\n"
                        f"Дата окончания подписки: {subscriptions_stop.strftime('%d.%m.%Y')}")
                else:
                    await message.answer(
                        f"Вы зарегистрированы!\nВаш email: {email}\n"
                        f"Дата окончания подписки: {subscriptions_stop.strftime('%d.%m.%Y')}\n"
                        f"Для продления подписки обратитесь в поддержку")
    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        print(f"Произошла ошибка: {str(e)}")
    finally:
        await pool.close()


@router.message(StateFilter(FSMFillForm.register))
async def process_register_email(message: Message, state: FSMContext):
    email = message.text.strip()
    check_email = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    result_email = check_email.match(email)
    if result_email:
        pool = await create_pool()
        async with pool.acquire() as conn:
            # Записываем сегодняшнюю дату в формате 'гггг.мм.дд'
            today = datetime.today()

            # # Вычисляем дату на неделю позже
            next_week = (datetime.today() + timedelta(days=7))

            await conn.execute('INSERT INTO users_bot (user_id, email, subscriptions_start, subscriptions_stop, access)'
                               'VALUES ($1, $2, $3, $4, $5)', message.from_user.id, email, today, next_week, True)
        await pool.close()
        await message.answer("Спасибо, вы зарегистрированы!")
        await state.clear()
    else:
        await message.answer(
            text='То, что вы отправили не похоже на email\n\n'
                 'Пожалуйста, введите ваше email\n\n'
                 'Если вы хотите прервать регистрацию - '
                 'отправьте команду\n /cancel'
        )


@router.message(Command(commands='status'), StateFilter(default_state))
async def process_subscription_status(message: Message, state: FSMContext):
    user_id = message.from_user.id
    pool = await create_pool()
    async with pool.acquire() as conn:
        try:
            await message.delete()
            user_data = await conn.fetchrow(
                'SELECT subscriptions_start, subscriptions_stop, access FROM users_bot WHERE user_id = $1',
                user_id
            )
            if user_data:
                subscriptions_start, subscriptions_stop, access = user_data
                if access:
                    message_text = (
                        f"Ваша подписка <b>активна</b>.\n"
                        f"Дата окончания подписки: {subscriptions_stop.strftime('%d.%m.%Y')}"
                    )
                else:
                    message_text = (f"Ваша подписка <b>Истекла</b>.\n"
                                    f"Дата окончания подписки: {subscriptions_stop.strftime('%d.%m.%Y')}")
            else:
                message_text = "Вы не зарегистрированы или у вас нет активной подписки."
        except Exception as e:
            message_text = f"Произошла ошибка: {e}"

        await message.answer(message_text)
    await pool.close()


@router.message(Command(commands='new_session'), StateFilter(default_state))
async def start_new_session(message: Message, state: FSMContext):
    await message.delete()
    # Отправляем запрос пользователю
    await message.answer('Если вы хотите прервать - '
                         'отправьте команду\n /cancel\n\n'
                         'Название не должно превышать 18 символов и в нем не должно быть "_"\n'
                         'Введите название новой сессии:')

    # Устанавливаем состояние ожидания названия сессии
    await state.set_state(FSMFillForm.waiting_for_session_name)


@router.message(StateFilter(FSMFillForm.waiting_for_session_name), F.text)
async def process_session_name(message: Message, state: FSMContext):
    session_name = message.text.strip()
    # Проверяем длину названия сессии
    if len(session_name) > 18:
        await message.answer(
            "Название сессии не должно быть длиннее 18 символов. Пожалуйста, выберите другое название.")
        return

    # Проверяем, что название сессии не пустое
    if not session_name:
        await message.answer("Название сессии не может быть пустым. Попробуйте еще раз.")
        return
        # Проверяем, что название сессии не содержит символ нижнего подчеркивания
    if '_' in session_name:
        await message.answer(
            "Название сессии не должно содержать символ нижнего подчеркивания (_). Попробуйте еще раз.")
        return

    pool = await create_pool()
    async with pool.acquire() as conn:
        user_id = message.from_user.id

        # Проверяем, существует ли уже сессия с таким названием для этого пользователя
        existing_session = await conn.fetchval(
            'SELECT sessions FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name
        )
        if existing_session:
            await message.answer('Если вы хотите прервать - '
                                 'отправьте команду\n /cancel\n\n'
                                 "Сессия с таким названием уже существует. Пожалуйста, выберите другое название.")
            return

        # Создаем новую сессию в таблице user_group
        await conn.execute('INSERT INTO user_group (user_id, sessions) VALUES ($1, $2)', user_id, session_name)

        # Создаем новую сессию в таблице words
        await conn.execute('INSERT INTO words (user_id, sessions) VALUES ($1, $2)', user_id, session_name)
    await pool.close()

    # Отправляем сообщение о создании сессии
    await message.answer(f"Сессия '{session_name}' создана.")

    # Сбрасываем состояние
    await state.clear()


# Этот хэндлер будет срабатывать, если во время ввода имени
# будет введено что-то некорректное
@router.message(StateFilter(FSMFillForm.waiting_for_session_name))
async def warning_not_name(message: Message):
    await message.answer(
        text='То, что вы отправили не похоже на имя\n\n'
             'Пожалуйста, введите имя\n\n'
             'Если вы хотите прервать заполнение - '
             'отправьте команду /cancel'
    )


@router.message(Command(commands='my_sessions'), StateFilter(default_state))
async def process_sessions_command(message: Message):
    pool = await create_pool()
    try:
        await message.delete()
        user_id = message.from_user.id
        async with pool.acquire() as conn:
            sessions = await conn.fetch(
                'SELECT sessions FROM user_group WHERE user_id = $1', user_id
            )
            # await pool.close()
        if sessions:
            # Формируем строку сессий для ответа пользователю
            # Используем множество для уникальных значений сессий
            session_set = set()
            for session in sessions:
                session_set.add(session[0])
            session_list = list(session_set)

            await message.answer(text=LEXICON[message.text],
                                 reply_markup=create_list_keyboard(*session_list))
        else:
            await message.answer("У вас нет активных сессий.")
    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        print(f"Произошла ошибка при получении списка сессий: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(F.data == '/my_sessions')
async def process_sessions_button(callback: CallbackQuery):
    pool = await create_pool()
    try:
        user_id = callback.message.chat.id
        await callback.message.delete()
        async with pool.acquire() as conn:
            sessions = await conn.fetch(
                'SELECT sessions FROM user_group WHERE user_id = $1', user_id
            )
            if sessions:
                # Формируем строку сессий для ответа пользователю
                # Используем множество для уникальных значений сессий
                session_set = set()
                for session in sessions:
                    session_set.add(session[0])
                session_list = list(session_set)
                await callback.message.answer(text=LEXICON['/my_sessions'],
                                              reply_markup=create_list_keyboard(*session_list))
            else:
                await callback.message.answer("У вас нет активных сессий.")
    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        await callback.message.answer(f"Произошла ошибка при получении списка сессий: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(F.data == 'edit_sessions')
async def process_edit_press(callback: CallbackQuery):
    pool = await create_pool()
    try:
        user_id = callback.from_user.id
        async with pool.acquire() as conn:
            sessions = await conn.fetch(
                'SELECT sessions FROM user_group WHERE user_id = $1', user_id
            )
            # await pool.close()

        if sessions:
            # Формируем строку сессий для ответа пользователю
            # Используем множество для уникальных значений сессий
            session_set = set()
            for session in sessions:
                session_set.add(session[0])
            session_list = list(session_set)

            await callback.message.edit_text(text=LEXICON[callback.data],
                                             reply_markup=create_edit_keyboard(*session_list))
        else:
            await callback.answer("У вас нет активных сессий.")
    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        await callback.answer(f"Произошла ошибка при получении списка сессий: {str(e)}")
        print(f"Произошла ошибка при получении списка сессий: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(lambda c: c.data[-6:] == 'delete')
async def process_del_bookmark_press(callback: CallbackQuery):
    pool = await create_pool()
    try:
        # Получаем идентификатор пользователя из колбэка
        user_id = callback.from_user.id
        # print(user_id)
        # Получаем ссылку на сессию из колбэка
        session_name = callback.data[:-7]
        async with pool.acquire() as conn:
            # Удаляем сессию из таблицы user_group
            await conn.execute('DELETE FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name)
            # Удаляем сессию из таблицы words
            await conn.execute('DELETE FROM words WHERE user_id = $1 AND sessions = $2', user_id,
                               session_name)
        async with pool.acquire() as conn:
            sessions = await conn.fetch(
                'SELECT sessions FROM user_group WHERE user_id = $1', user_id
            )

            if sessions:
                # Формируем строку сессий для ответа пользователю
                # Используем множество для уникальных значений сессий
                session_set = set()
                for session in sessions:
                    session_set.add(session[0])
                session_list = list(session_set)
                await callback.message.edit_text(text=LEXICON['/my_sessions'],
                                                 reply_markup=create_edit_keyboard(*session_list))
            else:
                await callback.message.delete()
                await callback.answer("У вас нет активных сессий.")

    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        await callback.answer(f"Произошла ошибка при удалении сессии: {str(e)}")

    finally:
        await pool.close()


@router.callback_query(F.data == 'cancel')
async def process_cancel_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.answer()
    await state.clear()


@router.callback_query(lambda c: c.data.startswith('session_name_'))
async def process_session_buttons(callback: CallbackQuery):
    pool = await create_pool()
    try:
        session_name = callback.data.split('_')[-1]
        user_id = callback.from_user.id
        async with pool.acquire() as conn:
            groups = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name)
            words = await conn.fetch(
                'SELECT words FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name)

        markup = buttons_words_group(session_name=session_name)
        await callback.message.edit_text(text=session_name, reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(lambda c: c.data.startswith('button_words_'))
async def process_words_button(callback: CallbackQuery):
    pool = await create_pool()
    session_name = callback.data.split('_')[-1]
    user_id = callback.from_user.id
    try:
        async with pool.acquire() as conn:
            words_query = await conn.fetchrow(
                'SELECT words, words_exception FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name)

        if not words_query:
            text = 'Список пуст'
        else:
            words, words_exception = words_query
            text = (f'Ключевые слова:\n{words if words else "список пуст"}\n\nСлова исключения:\n'
                    f'{words_exception if words_exception else "список пуст"}')

        markup = button_list_words(session_name=session_name)
        await callback.message.edit_text(text=text, reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

    finally:
        await pool.close()


@router.callback_query(lambda c: c.data.startswith('button_back_'))
async def process_back(callback: CallbackQuery):
    pool = await create_pool()
    try:
        session_name = callback.data.split('_')[-1]
        user_id = callback.from_user.id
        async with pool.acquire() as conn:
            groups = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name)
            words = await conn.fetch(
                'SELECT words FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name)

        markup = buttons_words_group(session_name=session_name)
        await callback.message.edit_text(text=session_name, reply_markup=markup)
    except Exception as e:
        await callback.answer(f"Произошла ошибка: {str(e)}")
    finally:
        await pool.close()


# Хендлер который отрабатывает изменения списка слов
@router.callback_query(lambda c: c.data.startswith('edit_words_'))
async def process_edit_words_button(callback: CallbackQuery, state: FSMContext, bot: Bot):
    pool = await create_pool()
    try:
        user_id = callback.from_user.id
        session_name = callback.data.split('_')[-1]
        words_type = 'words' if callback.data.split('_')[-2] == '0' else 'words_exception'

        await state.update_data(session_name=session_name)

        async with pool.acquire() as conn:
            words = await conn.fetch(
                f'SELECT {words_type} FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name)
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel')]])

        if not words[0][words_type]:

            await callback.message.edit_text(text="Введите новые слова через запятую:", reply_markup=markup)

        else:

            await callback.message.edit_text(text='Скопируйте список из сообщения '
                                                  'ниже и отправьте после внесения изменений.', reply_markup=markup)
            await callback.message.answer(text=words[0]['words'])

        if words_type == 'words':
            await state.set_state(FSMFillForm.edit_words)
        else:
            await state.set_state(FSMFillForm.edit_words_exceptions)
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")
    finally:
        await pool.close()


@router.message(StateFilter(FSMFillForm.edit_words), F.text)
async def process_edit_words(message: Message, state: FSMContext):
    pool = await create_pool()
    try:
        user_id = message.from_user.id
        data = await state.get_data()
        session_name = data.get('session_name')

        # Получаем новые ключевые слова из сообщения пользователя
        new_words = message.text.strip()

        async with pool.acquire() as conn:
            # Проверяем, существуют ли записи для данного пользователя и сеанса
            existing_words = await conn.fetchval(
                'SELECT words FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )

            if existing_words:
                # Запись существует, выполняем операцию UPDATE
                await conn.execute(
                    'UPDATE words SET words = $1 WHERE user_id = $2 AND sessions = $3',
                    new_words, user_id, session_name
                )
            else:
                # Запись не существует, выполняем операцию INSERT
                await conn.execute(
                    'UPDATE words SET words = $1 WHERE user_id = $2 AND sessions = $3',
                    new_words, user_id, session_name
                )

        await message.answer("Ключевые слова успешно обновлены.")
        markup = buttons_words_group(session_name=session_name)
        await message.answer(text=session_name, reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка при обновлении ключевых слов: {str(e)}")
    finally:
        await pool.close()
        await state.clear()


@router.message(StateFilter(FSMFillForm.edit_words_exceptions), F.text)
async def process_edit_words(message: Message, state: FSMContext):
    pool = await create_pool()
    try:
        user_id = message.from_user.id
        data = await state.get_data()
        session_name = data.get('session_name')

        # Получаем новые ключевые слова из сообщения пользователя
        new_words = message.text.strip()

        async with pool.acquire() as conn:
            # Проверяем, существуют ли записи для данного пользователя и сеанса
            existing_words = await conn.fetchval(
                'SELECT words_exception FROM words WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )

            if existing_words:
                # Запись существует, выполняем операцию UPDATE
                await conn.execute(
                    'UPDATE words SET words_exception = $1 WHERE user_id = $2 AND sessions = $3',
                    new_words, user_id, session_name
                )
            else:
                # Запись не существует,
                await conn.execute(
                    'UPDATE words SET words_exception = $1 WHERE user_id = $2 AND sessions = $3',
                    new_words, user_id, session_name
                )

        await message.answer("Слова исключения успешно обновлены.")
        markup = buttons_words_group(session_name=session_name)
        await message.answer(text=session_name, reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка при обновлении слов исключение: {str(e)}")
    finally:
        await pool.close()
        await state.clear()


# Хендлер будет срабатывать на нажатие кнопки "группы" и отображать список групп по определенной сессии
@router.callback_query(lambda c: c.data.startswith('button_groups_'))
async def process_group_list(callback: CallbackQuery):
    pool = await create_pool()
    try:
        # await message.delete()
        user_id = callback.from_user.id
        session_name = callback.data.split('_')[-1]
        async with pool.acquire() as conn:
            group_link = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )
            # await pool.close()
        if group_link:
            group_list = set()
            for group in group_link:
                group_list.add(group[0])
            groups_list = list(group_list)
            markup = create_list_group(*groups_list, session_name=session_name)
            await callback.message.answer("Ваши группы:", reply_markup=markup)

        else:
            button_back = InlineKeyboardButton(
                text='Назад',
                callback_data=f'button_back_{session_name}'
            )
            button_add_group = InlineKeyboardButton(
                text='Добавить',
                callback_data=f'button_add_g_{session_name}'
            )
            markup = InlineKeyboardMarkup(inline_keyboard=[[button_add_group, button_back]])
            await callback.message.edit_text(text="Список групп пуст. Хотите добавить группу?\n\n"
                                                  "Группы можно добавлять списком через запятую.",
                                             reply_markup=markup)


    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        print(f"Произошла ошибка при получении списка сессий: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(lambda c: c.data.startswith('button_add_g_'))
async def process_add_group(callback: CallbackQuery, state: FSMContext):
    try:
        session_name = callback.data.split('_')[-1]

        await state.update_data(session_name=session_name)
        await state.set_state(FSMFillForm.fill_add_group)

        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='cancel')]])

        await callback.message.edit_text(text='Пожалуйста, пришлите ссылку вида: https://t.me/your_group\n'
                                              'или @your_group\n'
                                              'Группы можно добавлять списком через запятую.\n\n'
                                              'Если вы хотите прервать - нажмите отмена',
                                         reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")


@router.message(StateFilter(FSMFillForm.fill_add_group), F.text)
async def process_add_groups(message: Message, state: FSMContext):
    pool = await create_pool()
    try:
        data = await state.get_data()
        session_name = data.get('session_name')
        user_id = message.from_user.id

        group_links = message.text.strip().split(',')
        valid_links = []
        invalid_links = []


        for link in group_links:
            link = link.strip()
            # Проверяем правильность формата ссылки
            if link.startswith('https://t.me/') or link.startswith('@'):
                async with pool.acquire() as conn:
                    existing_group = await conn.fetchval(
                        'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2 AND group_link = $3',
                        user_id, session_name, link
                    )
                if existing_group is None:
                    valid_links.append(link)
                else:
                    await message.answer(f"Группа '{link}' уже существует в базе данных.")

            else:
                invalid_links.append(link)


        async with pool.acquire() as conn:
            # Получаем текущий список групп для данного пользователя и сессии
            current_groups = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2',
                user_id, session_name
            )

            # Добавляем новые группы к текущему списку групп
            for link in valid_links:
                if link not in [group['group_link'] for group in current_groups]:
                    await conn.execute(
                        'INSERT INTO user_group (user_id, sessions, group_link) VALUES ($1, $2, $3)',
                        user_id, session_name, link
                    )

        if invalid_links:
            await message.answer(f"Следующие ссылки имеют неверный формат и не были добавлены:\n"
                                 f"{', '.join(invalid_links)}")
        await message.answer("Группы успешно добавлены.")

        async with pool.acquire() as conn:
            group_link = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )

        group_list = set()
        for group in group_link:
            group_list.add(group[0])
        groups_list = list(group_list)
        markup = create_list_group(*groups_list, session_name=session_name)
        await message.answer("Ваши группы:", reply_markup=markup)
    except Exception as e:
        print(f"Произошла ошибка при добавлении групп: {str(e)}")
    finally:
        await pool.close()
        await state.clear()


@router.callback_query(lambda c: c.data.startswith('edit_groups_'))
async def process_edit_groups(callback: CallbackQuery):
    pool = await create_pool()
    try:
        user_id = callback.from_user.id
        session_name = callback.data.split('_')[-1]
        async with pool.acquire() as conn:
            group_link = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )

        if group_link:
            group_list = set()
            for group in group_link:
                group_list.add(group[0])
            groups_list = list(group_list)
            markup = create_edit_keyboard_groups(*groups_list, session_name=session_name)
            await callback.message.answer(text="Ваши группы:", reply_markup=markup)
        else:
            await callback.answer("У вас нет групп")
    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        await callback.answer(f"Произошла ошибка при получении списка групп: {str(e)}")
        print(f"Произошла ошибка при получении списка групп: {str(e)}")
    finally:
        await pool.close()


@router.callback_query(lambda c: c.data[-9:] == 'delete_gr')
async def process_del_bookmark_press(callback: CallbackQuery):
    pool = await create_pool()
    try:
        # Получаем идентификатор пользователя из колбэка
        user_id = callback.from_user.id
        # print(user_id)
        # Получаем ссылку на сессию из колбэка
        group_link = callback.data[:-10]

        async with pool.acquire() as conn:
            sessions = await conn.fetch('SELECT sessions FROM user_group WHERE user_id = $1 AND group_link = $2',
                                        user_id, group_link)

        session_name = sessions[0]['sessions']

        async with pool.acquire() as conn:
            # Удаляем из таблицы user_group
            await conn.execute('DELETE FROM user_group WHERE user_id = $1 AND group_link = $2', user_id, group_link)

        async with pool.acquire() as conn:
            group_link = await conn.fetch(
                'SELECT group_link FROM user_group WHERE user_id = $1 AND sessions = $2', user_id, session_name
            )

        if group_link:
            group_list = set()
            for group in group_link:
                group_list.add(group[0])
            groups_list = list(group_list)
            markup = create_edit_keyboard_groups(*groups_list, session_name=session_name)
            await callback.message.answer(text="Ваши группы:", reply_markup=markup)
        else:
            await callback.answer("У вас нет групп")

    except Exception as e:
        # Обработка исключения, например, отправка сообщения об ошибке
        print(f"Произошла ошибка при удалении сессии: {str(e)}")

    finally:
        await pool.close()
