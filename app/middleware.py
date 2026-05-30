import logging
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message

logger = logging.getLogger(__name__)

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        logger.info(f"MSG from {user.id} (@{user.username}): {event.text or '[no text]'}")
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Ошибка от {user.id}: {e}", exc_info=True)
            await event.answer(
                "⚠️ Произошла ошибка\\. Попробуй ещё раз или напиши /start",
                parse_mode="MarkdownV2"
            )
