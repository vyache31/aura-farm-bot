import asyncio
import json
import re

from aiogram import Router, F, Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from bot_context.models import ChatMessage
from bot_context.storage import chat_context
from bot_context.llm_service import llm_service
from bot_context.llm_service import prompt_builder

router = Router()

ZHORA_STICKERS = {
    "facepalm": "CAACAgIAAyEFAAMBBCmMEwACA-FqXSI77KNRdZBYEy_Odmrj81NXlQACfWMAAqU8-UmGKUwpUnlq-T0E",
    "laugh": "CAACAgIAAyEFAAMBBCmMEwACA91qXSIbiYilT-sOTG7u3Tgyu3vEuQACFnAAArvT-Enp9yBOXasOKz0E",
    "angry": "CAACAgIAAyEFAAMBBCmMEwACA99qXSIy91eNFJ1hgUFbqiNrd0DETgACIGcAAkMy-UlFZevcjwcJnT0E",
    "cool": "CAACAgIAAyEFAAMBBCmMEwACA9tqXSGQWJ3l-lXj-i7luM3oRG5nxgAComwAAhGqEEqntnWEvUCDeD0E",
    "motya_moment": "CAACAgIAAyEFAAMBBCmMEwACBJJqXS1ku9CvIPx4js-PPDpk26hvFQAC_lwAAgYVCUrkcDqu-rnxvj0E"
}

import random
def should_zhora_intervene(chat_id):

    count = chat_context.message_counter.get(
        chat_id,
        0
    )

    if count < 20:
        return False

    if count > 30:
        return True


    return random.random() < 0.33

class ZhoraTrigger(BaseFilter):

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False

        text = message.text.lower()

        if (
            message.reply_to_message
            and message.reply_to_message.from_user.is_bot
        ):
            return True

        # @Жора
        if "@brat_zhori_Bot" in text:
            return True

        # просто имя Жора
        if re.search(r"\bжора\b", text):
            return True

        return False


print("Router intelligence загружен")
@router.message(F.text, ZhoraTrigger())
async def ai_answer(message: Message, bot: Bot):
    print("LOG: провалились в хэндлер")
    history = chat_context.get(
        message.chat.id
    )
    print("LOG: получили историю")
    prompt = prompt_builder.build(
        history
    )
    print("LOG: получили промпт. Вот он:")
    print(prompt)
    async with ChatActionSender.typing(
            bot=bot,
            chat_id=message.chat.id
    ):
        response = await llm_service.generate(prompt)

    print("LOG: получили ответ")

    try:
        data = json.loads(response)

    except Exception:
        print("LLM вернул мусор:", response)
        return

    action = data.get("action")

    if action == "ignore":
        return

    if action == "react":
        emoji = data.get("emoji", "👍")
        print("LOG EMOJI: бот хочет поставить ", emoji)

        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[
                {
                    "type": "emoji",
                    "emoji": emoji
                }
            ]
        )

        return

    if action == "reply":
        text = data.get("text")

        await message.reply(text)

        chat_context.add(
            chat_id=message.chat.id,
            message=ChatMessage(
                username="Жора",
                text=text,
                reply_to_username=(
                        message.from_user.username
                        or str(message.from_user.id)
                )
            )
        )

    if action == "sticker":
        await bot.send_chat_action(
            chat_id=message.chat.id,
            action="choose_sticker"
        )
        sticker_name = data.get("sticker")

        sticker_id = ZHORA_STICKERS.get(
            sticker_name
        )

        if not sticker_id:
            print(
                "Неизвестный стикер:",
                sticker_name
            )
            return

        await asyncio.sleep(1)
        await bot.send_sticker(
            chat_id=message.chat.id,
            sticker=sticker_id
        )

        chat_context.add(
            chat_id=message.chat.id,
            message=ChatMessage(
                username="Жора",
                text=f"[стикер: {sticker_name}]",
                reply_to_username=(
                        message.from_user.username
                        or str(message.from_user.id)
                )
            )
        )

        return