import logging
from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            user = event.from_user
            logger.info(f"MSG from {user.id}: {getattr(event, 'text', '')}")
        except Exception:
            pass
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка: {e}", exc_info=True)
            try:
                await event.answer("Попробуй ещё раз или напиши /start")
            except Exception:
                pass
