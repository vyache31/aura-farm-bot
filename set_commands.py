import asyncio
import os
from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat
)
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERS_ID = list(map(int, (os.getenv("ADMIN_USERS_ID")).split(';')))

async def main():
    async with Bot(token=TOKEN) as bot:
        for admin_id in ADMIN_USERS_ID:
            try:
                await bot.set_my_commands(
                    commands=[
                        BotCommand(
                            command="send",
                            description="отправить сообщение в чат"
                        ),
                        BotCommand(
                            command="setthreshold",
                            description="установить поздравлялку"
                        ),
                        BotCommand(
                            command="listthresholds",
                            description="посмотреть список поздравлялок"
                        ),
                        BotCommand(
                            command="removethreshold",
                            description="удалить поздравлялку"
                        ),
                    ],
                    scope=BotCommandScopeChat(
                        chat_id=admin_id
                    )
                )
            except Exception as err:
                print(f"ERROR LOG: {err}")
        print("LOG: команды админам заданы")

if __name__ == "__main__":
    asyncio.run(main())