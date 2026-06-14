import re
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import database as db
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

DB_PATH = "aura.db"

AURA_REGEX = re.compile(r"([+-]\d+)\s*aura", re.IGNORECASE)

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(Command("aura"))
async def aura_top(message: Message):
    top = await db.get_top(message.chat.id)

    if not top:
        await message.answer("Пока нет данных по ауре.")
        return

    text = "🏆 Топ по ауре:\n\n"
    for i, (username, aura) in enumerate(top, start=1):
        name = username or "Ноунейм"
        text += f"{i}. {name} — {aura}\n"

    await message.answer(text)


@dp.message(Command("change_name"))
async def change_name(message: Message):
    name = message.text.replace("/change_name", "").strip()

    try:
        await db.change_username(
            message.from_user.id,
            message.chat.id,
            name
        )
    except Exception as err:
        print(f"LOG ERROR: {err}")
        await message.answer("я чломался(")
        return

    await message.answer(f"ок, {name}")


@dp.message(F.reply_to_message)
async def handle_aura(message: Message):
    text = message.text or ""
    match = AURA_REGEX.search(text)

    if not match:
        return

    delta = int(match.group(1))

    target = message.reply_to_message.from_user
    if not target:
        return

    username = target.username or target.full_name

    await db.update_aura(
        target.id,
        message.chat.id,
        username,
        delta
    )


async def main():
    await db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
