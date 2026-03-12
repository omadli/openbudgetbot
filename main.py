import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from tortoise import Tortoise
from aiogram.client.default import DefaultBotProperties

from settings import BOT_TOKEN
from db.config import TORTOISE_ORM
from handlers.user import user_router
from handlers.admin import admin_router
from handlers.games import games_router
from middlewares.subscribe import CheckSubscriptionMiddleware


async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    # await Tortoise.generate_schemas()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # DB inisializatsiyasi
    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    # Routerlarni ulash
    # dp.message.middleware(CheckSubscriptionMiddleware())
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(games_router)

    try:
        print("Bot ishga tushdi...")
        await dp.start_polling(bot)
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
