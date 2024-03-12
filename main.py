# from telethon import TelegramClient, events  # импортируем библиотеки
# from pars_conf import account, list_all  # импортируем данные из файл конфигурации
# api_id = account[0]  # задаем API
# api_hash = account[1]  #задаем HASH
# client = TelegramClient('my_account', api_id, api_hash)  # собираем клиента
# @client.on(events.NewMessage)  # ждём новое сообщение
# async def my_event_handler(event):  # функция обрабатывающая пришедшее сообщение
#         if event.chat.username in list_all:  # проверяем пришло ли событие из канала который входит в наш список
#                 chat = await event.get_input_chat()  # получем реквизиты чата из которого пришло сообщение
#                 msg = await client.get_messages(chat.channel_id, limit=1)  # берем последнее сообщение из полученого чата
#                 await client.forward_messages(int(account[2]), msg)  # пересылаем сообщение в наш чат
#                 print("busted")
# client.start()  # запускаем клиент
# client.run_until_disconnected()  # подерживаем клиент в рабочем состоянии

import asyncio
import logging

from aiogram import Bot, Dispatcher
from config_data.config import Config, load_config
from handlers import other_hendlers, user_hendlers
from utils import functions
from keyboards.main_menu import set_main_menu
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] #%(levelname)-8s %(filename)s:'
           '%(lineno)d - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main() -> None:
    config: Config = load_config()

    bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
    dp = Dispatcher()

    # Создаем планировщик
    scheduler = AsyncIOScheduler(timezone='Asia/Tbilisi')

    # Добавляем задачу для выполнения функции каждый день в полночь
    scheduler.add_job(functions.daily_check_subscription,
                      trigger='cron', hour=0, minute=3, kwargs={'bot': bot})
    scheduler.add_job(functions.send_notifications_to_expiring_users, trigger='cron',
                      hour=datetime.now().hour, minute=datetime.now().minute + 1, kwargs={'bot': bot})
    # Запускаем планировщик
    scheduler.start()

    # Настраиваем главное меню бота
    await set_main_menu(bot)
    # Регистриуем роутеры в диспетчере
    dp.include_router(user_hendlers.router)
    dp.include_router(other_hendlers.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())