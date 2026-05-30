import asyncio
import logging
import logging.handlers
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.database import init_db
from app.handlers import router_user, router_admin
from app.middleware import AccessMiddleware

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env!")

Path("logs").mkdir(exist_ok=True)
log_handler = logging.handlers.RotatingFileHandler(
    "logs/bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[log_handler, logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Инициализация базы данных...")
    await init_db()
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
    dp = Dispatcher()
    dp.message.middleware(AccessMiddleware())
    dp.include_router(router_admin)
    dp.include_router(router_user)
    logger.info("Бот запущен!")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
