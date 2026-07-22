import re
from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, ReactionTypeEmoji
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
import words
from bot_context.models import ChatMessage
from bot_context.storage import chat_context

router = Router()
AURA_REGEX = re.compile(r"([+-]\s*\d+)\s*аур[аы]?", re.IGNORECASE)

class ChangeUsername(StatesGroup):
    waiting_for_name = State()

def build_leaderboard(top):
    text = "🏆 Топ по ауре:\n\n"
    for i, (username, aura) in enumerate(top, start=1):
        name = username or "Ноунейм"
        text += f"{i}. {name} — {aura}\n"
    now = (datetime.now() + timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
    text += f"\nя считал в {now}"
    return text

async def update_leaderboard(bot: Bot, chat_id: int):
    top = await db.get_top(chat_id)
    if not top:
        return
    text = build_leaderboard(top)
    message_id = await db.get_leaderboard_message(chat_id)
    if not message_id:
        return
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
    except:
        await db.save_leaderboard_message(chat_id, None)

@router.message(Command("aura"))
async def aura_top(message: Message, bot: Bot):
    top = await db.get_top(message.chat.id)
    text = build_leaderboard(top) if top else "пока без ауры"

    last_message_id = await db.get_leaderboard_message(message.chat.id)
    if last_message_id:
        try:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=last_message_id, text=text)
        except Exception as err:
            print("EDIT ERROR:", repr(err))
            await db.save_leaderboard_message(message.chat.id, None)

    sent = await message.answer(text)
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
    await db.save_leaderboard_message(message.chat.id, sent.message_id)

@router.message(Command("change_name"))
async def change_name(message: Message, state: FSMContext):
    await message.reply("и как?")
    await state.set_state(ChangeUsername.waiting_for_name)

@router.message(ChangeUsername.waiting_for_name)
async def process_new_name(message: Message, state: FSMContext, bot: Bot):
    new_name = message.text.strip()
    await db.change_username(message.from_user.id, message.chat.id, new_name)
    await bot.set_message_reaction(
        chat_id=message.chat.id,
        message_id=message.message_id,
        reaction=[ReactionTypeEmoji(emoji="👌")]
    )
    await message.answer(f"oke, {new_name}")
    await state.clear()

@router.message(F.reply_to_message & F.text)
async def handle_aura(message: Message, bot: Bot):
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
            reaction=[ReactionTypeEmoji(emoji="👎")]
        )
    else:
        await bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji(emoji="❤️")]
        )

    username = target.username or target.full_name
    await db.update_aura(target.id, message.chat.id, username, delta)
    new_aura = await db.get_aura(target.id, message.chat.id)

    thresholds = await db.get_thresholds(message.chat.id)
    for thr, msgs in thresholds:
        if new_aura >= thr and not await db.is_group_notification_sent(message.chat.id, thr):
            for msg_data in msgs:
                try:
                    await bot.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=msg_data['chat_id'],
                        message_id=msg_data['message_id']
                    )
                except Exception as err:
                    await bot.send_message(
                        chat_id=msg_data['data_id'],
                        text=f"я не смог отправить сообщение в {message.chat.full_name} :(\n"
                            f"\n{err}"
                    )
            await db.mark_group_notification_sent(message.chat.id, thr)

    await update_leaderboard(bot, message.chat.id)