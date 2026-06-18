import re
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReactionTypeEmoji, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import database as db
import os
from dotenv import load_dotenv
import words
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))
DB_PATH = "aura.db"

AURA_REGEX = re.compile(r"([+-]\s*\d+)\s*аур[аы]?", re.IGNORECASE)

bot = Bot(token=TOKEN)
dp = Dispatcher()

class ChangeUsername(StatesGroup):
    waiting_for_name = State()

class SendStates(StatesGroup):
    selecting_chat = State()
    waiting_text = State()
    confirming = State()

def build_leaderboard(top):
    text = "🏆 Топ по ауре:\n\n"

    for i, (username, aura) in enumerate(top, start=1):
        name = username or "Ноунейм"
        text += f"{i}. {name} — {aura}\n"

    now = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    text += f"\nя считал в {now}"

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
        text
    )

    await db.save_leaderboard_message(
        message.chat.id,
        sent.message_id
    )



@dp.message(Command("change_name"))
async def change_name(message: Message, state: FSMContext):
    await message.reply("и как?")
    await state.set_state(ChangeUsername.waiting_for_name)

@dp.message(ChangeUsername.waiting_for_name)
async def process_new_name(message: Message, state: FSMContext):
    new_name = message.text.strip()

    await db.change_username(
        message.from_user.id,
        message.chat.id,
        new_name
    )

    await bot.set_message_reaction(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reaction=[
            ReactionTypeEmoji(emoji="👌")
        ]
    )

    await message.answer(f"oke, {new_name}")

    await state.clear()


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
            text=text
        )
    except:
        await db.save_leaderboard_message(message.chat.id, None)

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
    if abs(delta) > 3000:
        from random import choice
        await message.answer(choice(words.phrases_too_much))
        return
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

    if target.id == message.from_user.id:
        from random import choice, randint
        delta = randint(-1000, -1)
        await message.answer(choice(words.phrases))
        await message.answer(f"на тебе {delta} очков")
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[
                ReactionTypeEmoji(emoji="👎")
            ]
        )

    else:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[
                ReactionTypeEmoji(emoji="❤️")
            ]
        )

    username = target.username or target.full_name

    await db.update_aura(
        target.id,
        message.chat.id,
        username,
        delta
    )

    await update_leaderboard(message)

@dp.message(Command("send"))
async def cmd_send(message: Message, state: FSMContext):
    if message.chat.type != "private" or message.from_user.id != ADMIN_USER_ID:
        await message.answer("⛔ Эта команда доступна только администратору в личных сообщениях.")
        return

    chat_ids = await db.get_all_chat_ids()
    if not chat_ids:
        await message.answer("📭 Нет доступных чатов для отправки.")
        return

    buttons = []
    for chat_id in chat_ids[:20]:
        try:
            chat = await bot.get_chat(chat_id)
            name = chat.title or chat.first_name or f"Чат {chat_id}"
        except:
            name = f"Чат {chat_id}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"send_chat_{chat_id}")])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="send_cancel")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📨 Выберите чат для отправки сообщения:", reply_markup=keyboard)
    await state.set_state(SendStates.selecting_chat)

@dp.callback_query(SendStates.selecting_chat)
async def process_chat_selection(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "send_cancel":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отправка отменена.")
        await state.clear()
        return

    if not data.startswith("send_chat_"):
        await callback.answer("Неизвестная команда.")
        return

    chat_id = int(data.split("_")[2])
    await state.update_data(selected_chat_id=chat_id)

    await callback.answer(f"Выбран чат {chat_id}")
    await callback.message.edit_text(f"📝 Введите текст сообщения для отправки в чат {chat_id}:")

    await state.set_state(SendStates.waiting_text)

@dp.message(SendStates.waiting_text, F.text)
async def process_message_text(message: Message, state: FSMContext):
    await state.update_data(text_to_send=message.text)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="send_confirm")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="send_cancel")]
    ])

    await message.answer(
        f"✉️ Сообщение будет отправлено:\n\n{message.text}\n\nПодтвердите действие:",
        reply_markup=keyboard
    )
    await state.set_state(SendStates.confirming)

@dp.callback_query(SendStates.confirming)
async def process_send_confirm(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "send_cancel":
        await callback.answer("Отменено.")
        await callback.message.edit_text("❌ Отправка отменена.")
        await state.clear()
        return

    if data != "send_confirm":
        await callback.answer("Неизвестная команда.")
        return

    user_data = await state.get_data()
    chat_id = user_data.get("selected_chat_id")
    text = user_data.get("text_to_send")

    if not chat_id or not text:
        await callback.answer("Ошибка: данные не найдены.")
        await state.clear()
        return

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        await callback.answer("✅ Сообщение отправлено!")
        await callback.message.edit_text(f"✅ Сообщение успешно отправлено в чат {chat_id}.")
    except Exception as e:
        await callback.answer("❌ Ошибка при отправке.")
        await callback.message.edit_text(f"❌ Не удалось отправить сообщение:\n{e}")

    await state.clear()

@dp.message(SendStates.waiting_text)
async def process_non_text(message: Message):
    await message.answer("⛔ Пожалуйста, отправьте текстовое сообщение.")

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий.")
        return
    await state.clear()
    await message.answer("Действие отменено.")


async def main():
    await db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
