import aiosqlite

DB_PATH = "aura.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT,
            aura INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chat_id)
        )
        """)
        await db.commit()


async def update_aura(user_id: int, chat_id: int, username: str, delta: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, chat_id, username, aura)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            aura = aura + ?,
            username = excluded.username
        """, (user_id, chat_id, username, delta, delta))
        await db.commit()


async def get_top(chat_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        SELECT username, aura
        FROM users
        WHERE chat_id = ?
        ORDER BY aura DESC
        LIMIT ?
        """, (chat_id, limit))
        return await cursor.fetchall()


async def change_username(user_id: int, chat_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, chat_id, username, aura)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            username = excluded.username
        """, (user_id, chat_id, username))
        await db.commit()