from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

from bot_context.models import ChatMessage
from bot_context.storage import chat_context


class ContextMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any]
    ):
        if event.message and event.message.text and event.message.from_user:
            msg = event.message
            print("MIDDLEWARE:", msg.from_user.username, msg.text, "reply:", bool(msg.reply_to_message))
            chat_context.add(
                chat_id=msg.chat.id,
                message=ChatMessage(
                    username=msg.from_user.username or str(msg.from_user.id),
                    text=msg.text,
                    reply_to_username=(
                        msg.reply_to_message.from_user.username
                        if msg.reply_to_message and msg.reply_to_message.from_user
                        else None
                    )
                )
            )
            count = chat_context.increment_counter(
                msg.chat.id
            )
        return await handler(event, data)

