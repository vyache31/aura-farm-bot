import re
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
import database as db
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

DB_PATH = "aura.db"

AURA_REGEX = re.compile(r"([+-]\s*\d+)\s*аур[аы]?", re.IGNORECASE)

bot = Bot(token=TOKEN)
dp = Dispatcher()

def build_leaderboard(top):
    text = "🏆 Топ по ауре:\n\n"

    for i, (username, aura) in enumerate(top, start=1):
        name = username or "Ноунейм"
        text += f"{i}. {name} — {aura}\n"

    now = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    text += f"\n_актуально на {now}_"

    return text


@dp.message(Command("aura"))
async def aura_top(message: Message):
    top = await db.get_top(message.chat.id)

    text = build_leaderboard(top) if top else "пока без ауры"

    last_message_id = await db.get_leaderboard_message(message.chat.id)

    if last_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=last_message_id,
                text=text
            )

        except Exception as err:
            print("EDIT ERROR:", repr(err))

            # если не получилось — чистим старое значение
            await db.save_leaderboard_message(message.chat.id, None)

    sent = await message.answer(
        text,
        parse_mode="Markdown")

    await db.save_leaderboard_message(
        message.chat.id,
        sent.message_id
    )

@dp.message(Command("change_name"))
async def change_name(message: Message):
    name = message.text.strip().split()

    if len(name) == 1:
        await message.answer("имя то введи епта")
        return
    try:
        await db.change_username(
            message.from_user.id,
            message.chat.id,
            name[1]
        )
    except Exception as err:
        print(f"LOG ERROR: {err}")
        await message.answer("я чломался(")
        return

    await message.answer(f"ок, {' '.join(name[1:])}")


async def update_leaderboard(message: Message):
    top = await db.get_top(message.chat.id)

    if not top:
        return

    text = build_leaderboard(top)

    message_id = await db.get_leaderboard_message(message.chat.id)

    if not message_id:
        return

    try:
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message_id,
            text=text,
            parse_mode="Markdown"
        )
    except:
        pass

@dp.message(F.reply_to_message & F.text)
async def handle_aura(message: Message):
    print("MESSAGE:", message.text)

    text = message.text or ""

    match = AURA_REGEX.search(text)

    print("MATCH:", match)

    if not match:
        return

    raw = match.group(1)
    delta = int(raw.replace(" ", ""))
    target = message.reply_to_message.from_user

    print(
        "TARGET:",
        target.id,
        target.username,
        target.full_name
    )

    print(
        "AUTHOR:",
        message.from_user.id,
        message.from_user.username
    )
    if not target:
        return

    # нельзя начислять самому себе (по желанию)
    if target.id == message.from_user.id:
        await message.answer("ты по моему что то попутал..")

    username = target.username or target.full_name

    await db.update_aura(
        target.id,
        message.chat.id,
        username,
        delta
    )

    await update_leaderboard(message)


async def main():
    await db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
