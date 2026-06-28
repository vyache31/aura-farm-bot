from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
from dotenv import load_dotenv

import database as db

load_dotenv()
router = Router()
ADMIN_USER_ID = list(map(int, (os.getenv("ADMIN_USERS_ID")).split(';')))

class SendStates(StatesGroup):
    selecting_chat = State()
    waiting_content = State()
    confirming = State()

class SetThresholdStates(StatesGroup):
    selecting_chat = State()
    waiting_value = State()
    waiting_messages = State()

class RemoveThresholdStates(StatesGroup):
    selecting_chat = State()
    selecting_thr = State()

# ======== Отправка сообщений ============
@router.message(Command("send"))
async def cmd_send(message: Message, state: FSMContext, bot: Bot):
    if message.chat.type != "private" or message.from_user.id not in ADMIN_USER_ID:
        await message.answer("⛔ только для админа в личке")
        return

    chat_ids = await db.get_all_chat_ids()
    if not chat_ids:
        await message.answer("📭 чатов пока нет")
        return

    buttons = []
    for chat_id in chat_ids[:20]:
        try:
            chat = await bot.get_chat(chat_id)
            name = chat.title or chat.first_name or f"Чат {chat_id}"
        except:
            name = f"Чат {chat_id}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"send_chat_{chat_id}")])

    buttons.append([InlineKeyboardButton(text="❌ отмена", callback_data="send_cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📨 куда отправляем?", reply_markup=keyboard)
    await state.set_state(SendStates.selecting_chat)

@router.callback_query(SendStates.selecting_chat)
async def process_chat_selection(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "send_cancel":
        await callback.answer("ладно, отменил")
        await callback.message.edit_text("❌ отправка отменена")
        await state.clear()
        return

    if not data.startswith("send_chat_"):
        await callback.answer("че за команда?")
        return

    chat_id = int(data.split("_")[2])
    await state.update_data(selected_chat_id=chat_id)

    await callback.answer(f"выбран чат {chat_id}")
    await callback.message.edit_text("📝 отправь сообщение, которое надо переслат:")
    await state.set_state(SendStates.waiting_content)

@router.message(SendStates.waiting_content)
async def process_content(message: Message, state: FSMContext):
    await state.update_data(
        source_chat_id=message.chat.id,
        source_message_id=message.message_id
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ пуск", callback_data="send_confirm")],
        [InlineKeyboardButton(text="❌ отмена", callback_data="send_cancel")]
    ])

    await message.answer("✉️ отправляю сообщение?", reply_markup=keyboard)
    await state.set_state(SendStates.confirming)

@router.callback_query(SendStates.confirming)
async def process_send_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = callback.data
    if data == "send_cancel":
        await callback.answer("отменил")
        await callback.message.edit_text("❌ отправка отменена")
        await state.clear()
        return

    if data != "send_confirm":
        await callback.answer("че за команда?")
        return

    user_data = await state.get_data()
    chat_id = user_data.get("selected_chat_id")
    source_chat_id = user_data.get("source_chat_id")
    source_message_id = user_data.get("source_message_id")

    if not chat_id or not source_chat_id or not source_message_id:
        await callback.answer("я сломався: данные не найдены.")
        await state.clear()
        return

    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=source_chat_id,
            message_id=source_message_id
        )
        await callback.answer("✅ сообщение отправлено!")
        await callback.message.edit_text(f"✅ сообщение успешно отправлено в чат {chat_id}.")
    except Exception as e:
        await callback.answer("❌ ошибка при отправке")
        await callback.message.edit_text(f"❌ не удалось отправить сообщение:\n{e}")

    await state.clear()

# ====== Пороги ============
@router.message(Command("setthreshold"))
async def cmd_set_threshold(message: Message, state: FSMContext, bot: Bot):
    if message.chat.type != "private" or message.from_user.id not in ADMIN_USER_ID:
        await message.answer("⛔ это только для избранных бро")
        return

    chat_ids = await db.get_all_chat_ids()
    if not chat_ids:
        await message.answer("📭 чатов пока нет")
        return

    buttons = []
    for chat_id in chat_ids[:20]:
        try:
            chat = await bot.get_chat(chat_id)
            name = chat.title or chat.first_name or f"Чат {chat_id}"
        except:
            name = f"Чат {chat_id}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"setthr_chat_{chat_id}")])

    buttons.append([InlineKeyboardButton(text="❌ отмена", callback_data="setthr_cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📌 выбери чат, для которого устанавливаем отметку ауры:", reply_markup=keyboard)
    await state.set_state(SetThresholdStates.selecting_chat)

@router.callback_query(SetThresholdStates.selecting_chat)
async def process_set_threshold_chat(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "setthr_cancel":
        await callback.answer("отменил")
        await callback.message.edit_text("❌ установка порога отменена")
        await state.clear()
        return

    if not data.startswith("setthr_chat_"):
        await callback.answer("че за команда?")
        return

    chat_id = int(data.split("_")[2])
    await state.update_data(selected_chat_id=chat_id)

    await callback.answer(f"выбран чат {chat_id}")
    await callback.message.edit_text("✏️ введи количество ауры:")
    await state.set_state(SetThresholdStates.waiting_value)

@router.message(SetThresholdStates.waiting_value)
async def process_threshold_value(message: Message, state: FSMContext):
    try:
        threshold = int(message.text.strip())
    except ValueError:
        await message.answer("❌ введи целое число бро")
        return

    if threshold <= 0:
        await message.answer("❌ порог должен быть положительным числом")
        return

    data = await state.get_data()
    chat_id = data.get("selected_chat_id")
    existing = await db.get_threshold(chat_id, threshold)
    if existing is not None:
        await message.answer(f"❌ порог {threshold} уже установлен для этого чата. используйте /removethreshold для удаления")
        return

    await state.update_data(threshold=threshold, messages=[])
    await message.answer(
        f"✅ порог {threshold} выбран.\n\n"
        "Теперь отправляй текстовые сообщения, которые будут отправлены при достижении порога\n"
        "каждое новое сообщение будет добавлено\n"
        "Когда закончишь, введи /done"
    )
    await state.set_state(SetThresholdStates.waiting_messages)

@router.message(SetThresholdStates.waiting_messages)
async def process_threshold_messages(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == "/done":
        data = await state.get_data()
        chat_id = data.get("selected_chat_id")
        threshold = data.get("threshold")
        messages = data.get("messages", [])

        if not messages:
            await message.answer("❌ ты не отправил ни одного сообщения. добавь хотя бы одно или отмени командой /cancel")
            return

        await db.add_threshold(chat_id, threshold, messages)
        await message.answer(f"✅ порог {threshold} сохранён с {len(messages)} сообщениями")
        await message.answer("проверь в /listthresholds сообщения для порога на всякий случай")
        await state.clear()
        return

    data = await state.get_data()
    messages = data.get("messages", [])
    messages.append({
        "chat_id": message.chat.id,
        "message_id": message.message_id
    })
    await state.update_data(messages=messages)
    await message.answer(f"📩 сообщение добавлено (всего {len(messages)}). Отправь ещё или /done для завершения")

@router.message(Command("done"))
async def cmd_done(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != SetThresholdStates.waiting_messages:
        await message.answer("❌ сейчас не идёт сбор сообщений")
        return

    await process_threshold_messages(message, state)

@router.message(Command("listthresholds"))
async def cmd_list_thresholds(message: Message, bot: Bot):
    if message.chat.type != "private" or message.from_user.id not in ADMIN_USER_ID:
        await message.answer("⛔ это только для избранных бро")
        return

    chat_ids = await db.get_all_chat_ids()
    if not chat_ids:
        await message.answer("📭 нет чатов")
        return

    buttons = []
    for chat_id in chat_ids[:20]:
        try:
            chat = await bot.get_chat(chat_id)
            name = chat.title or chat.first_name or f"Чат {chat_id}"
        except:
            name = f"Чат {chat_id}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"listthr_chat_{chat_id}")])

    buttons.append([InlineKeyboardButton(text="❌ отмена", callback_data="listthr_cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("📊 выберите чат для просмотра порогов:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith("listthr_"))
async def process_list_thresholds(callback: CallbackQuery):
    data = callback.data
    if data == "listthr_cancel":
        await callback.answer("отменил")
        await callback.message.edit_text("❌ просмотр отменён")
        return

    if not data.startswith("listthr_chat_"):
        await callback.answer("че за команда?")
        return

    chat_id = int(data.split("_")[2])
    thresholds = await db.get_thresholds(chat_id)
    if not thresholds:
        text = f"в чате {chat_id} нет установленных порогов"
    else:
        text = f"📋 пороги для чата {chat_id}:\n\n"
        for thr, msgs in thresholds:
            text += f"• {thr} — {len(msgs)} сообщений:\n"

    await callback.answer()
    await callback.message.edit_text(text)

@router.message(Command("removethreshold"))
async def cmd_remove_threshold(message: Message, state: FSMContext, bot: Bot):
    if message.chat.type != "private" or message.from_user.id not in ADMIN_USER_ID:
        await message.answer("⛔ это только для избранных бро")
        return

    chat_ids = await db.get_all_chat_ids()
    if not chat_ids:
        await message.answer("📭 нет чатов")
        return

    buttons = []
    for chat_id in chat_ids[:20]:
        try:
            chat = await bot.get_chat(chat_id)
            name = chat.title or chat.first_name or f"Чат {chat_id}"
        except:
            name = f"Чат {chat_id}"
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"remthr_chat_{chat_id}")])

    buttons.append([InlineKeyboardButton(text="❌ отмена", callback_data="remthr_cancel")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🗑 выбери чат для удаления порога:", reply_markup=keyboard)
    await state.set_state(RemoveThresholdStates.selecting_chat)

@router.callback_query(RemoveThresholdStates.selecting_chat)
async def process_remove_threshold_chat(callback: CallbackQuery, state: FSMContext):
    data = callback.data
    if data == "remthr_cancel":
        await callback.answer("отменил")
        await callback.message.edit_text("❌ удаление отменено")
        await state.clear()
        return

    if not data.startswith("remthr_chat_"):
        await callback.answer("че за команда?")
        return

    chat_id = int(data.split("_")[2])
    thresholds = await db.get_thresholds(chat_id)
    if not thresholds:
        await callback.answer("в этом чате нет порогов")
        await callback.message.edit_text("📭 в этом чате нет установленных порогов")
        return

    buttons = []
    for thr, _ in thresholds:
        buttons.append([InlineKeyboardButton(text=str(thr), callback_data=f"remthr_do_{chat_id}_{thr}")])
    buttons.append([InlineKeyboardButton(text="❌ отмена", callback_data="remthr_cancel")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"выберите порог для удаления в чате {chat_id}:",
        reply_markup=keyboard
    )
    await state.set_state(RemoveThresholdStates.selecting_thr)
    await callback.answer()

@router.callback_query(RemoveThresholdStates.selecting_thr)
async def process_remove_threshold_do(callback: CallbackQuery, state: FSMContext):
    if callback.data == "remthr_cancel":
        await callback.answer("отменил")
        await callback.message.edit_text("❌ удаление отменено")
        await state.clear()
        return
    parts = callback.data.split("_")
    if len(parts) != 4:
        await callback.answer("ошибка формата")
        return
    chat_id = int(parts[2])
    threshold = int(parts[3])

    await db.delete_threshold(chat_id, threshold)
    await callback.answer(f"порог {threshold} удалён")
    await callback.message.edit_text(f"✅ порог {threshold} успешно удалён из чата {chat_id}")