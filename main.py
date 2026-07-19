import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command
from middlewares import context_middleware

import database as db
from middlewares.context_middleware import ContextMiddleware
from routes import aura, admin, intelligence

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

dp.update.middleware(ContextMiddleware())

dp.include_router(intelligence.router)
dp.include_router(aura.router)
dp.include_router(admin.router)


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("нет активных действий")
        return
    await state.clear()
    await message.answer("действие отменено")

async def main():
    await db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())