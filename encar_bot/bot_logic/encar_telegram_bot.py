import os

import asyncio
from aiogram import F, Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters.command import Command
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from bot_logic.utils.handlers import router


async def start_bot():
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    TOKEN = os.environ.get('TELEGRAM_TOKEN')

    storage = RedisStorage.from_url(os.environ.get('CELERY_BACKEND'))
    asyncio.run(start_bot())
