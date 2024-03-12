import os
from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]


@dataclass
class Pyrogram:
    api_id: int
    api_hash: str


@dataclass
class BotBD:
    bd: str
    bot: str
@dataclass
class Postgres:
    ip: str
    pguser: str
    pgpassword: str
    database: str


@dataclass
class Config:
    tg_bot: TgBot
    pyrogram: Pyrogram
    bot_d: BotBD
    postgres: Postgres


# Создаем функцию, которая будет читать файл .env и возвращать
# экземпляр класса Config с заполненными полями token и admin_ids
def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    return Config(
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            admin_ids=list(map(int, env.list('ADMIN_IDS')))
        ),
        pyrogram=Pyrogram(
            api_id=env('API_ID'),
            api_hash=env('API_HASH')
        ),
        bot_d=BotBD(
            bd=env('BD'),
            bot=env('BOT')

        ),
        postgres=Postgres(
            ip=env('IP'),
            pguser=env('PGUSER'),
            pgpassword=env('PGPASSWORD'),
            database=env('DATABASE')
        )
    )

