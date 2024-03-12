import asyncpg

from datetime import datetime, timedelta
from aiogram import Bot
from config_data.config import Config, load_config


config: Config = load_config()




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


# В этой функции мы вычисляем дату окончания подписки через 3 дня
async def get_users_with_expiring_subscription():
    pool = await create_pool()
    async with pool.acquire() as conn:
        today = datetime.today()
        expiration_date = (today + timedelta(days=3)).date()
        expiring_users = await conn.fetch(
            'SELECT user_id FROM users_bot WHERE subscriptions_stop = $1 AND access = True',
            expiration_date
        )
    await pool.close()
    return [user['user_id'] for user in expiring_users]

#  Делаем рассылку, что подписка закончилась
async def send_notifications_to_expiring_users(bot: Bot):
    expiring_users = await get_users_with_expiring_subscription()
    for user_id in expiring_users:
        await bot.send_message(user_id, "Ваша подписка скоро истекает. Для продления обратитесь в поддержку.")


