import json
import aiosqlite

DB_PATH = "data/aura.db"

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
        await db.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard_messages (
            chat_id INTEGER PRIMARY KEY,
            message_id INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            chat_id INTEGER,
            threshold INTEGER,
            messages TEXT,
            PRIMARY KEY (chat_id, threshold)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS group_notification_sent (
            chat_id INTEGER,
            threshold INTEGER,
            PRIMARY KEY (chat_id, threshold)
        )
        """)
        await db.commit()

async def save_leaderboard_message(chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO leaderboard_messages (chat_id, message_id)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET message_id = excluded.message_id
        """, (chat_id, message_id))
        await db.commit()

async def get_leaderboard_message(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT message_id FROM leaderboard_messages WHERE chat_id = ?", (chat_id,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def update_aura(user_id: int, chat_id: int, username: str, delta: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, chat_id, username, aura)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET
            aura = aura + excluded.aura,
            username = excluded.username
        """, (user_id, chat_id, username, delta))
        await db.commit()

async def get_top(chat_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
        SELECT username, aura FROM users
        WHERE chat_id = ?
        ORDER BY aura DESC LIMIT ?
        """, (chat_id, limit))
        return await cursor.fetchall()

async def change_username(user_id: int, chat_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        INSERT INTO users (user_id, chat_id, username, aura)
        VALUES (?, ?, ?, 0)
        ON CONFLICT(user_id, chat_id) DO UPDATE SET username = excluded.username
        """, (user_id, chat_id, username))
        await db.commit()

async def get_all_chat_ids():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT chat_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def get_aura(user_id: int, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT aura FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def add_threshold(chat_id: int, threshold: int, messages: list[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        messages_json = json.dumps(messages, ensure_ascii=False)
        await db.execute("""
        INSERT OR REPLACE INTO thresholds (chat_id, threshold, messages)
        VALUES (?, ?, ?)
        """, (chat_id, threshold, messages_json))
        await db.commit()

async def get_thresholds(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT threshold, messages FROM thresholds WHERE chat_id = ?", (chat_id,))
        rows = await cursor.fetchall()
        return [(row[0], json.loads(row[1])) for row in rows]

async def get_threshold(chat_id: int, threshold: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT messages FROM thresholds WHERE chat_id = ? AND threshold = ?", (chat_id, threshold))
        row = await cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None

async def delete_threshold(chat_id: int, threshold: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM thresholds WHERE chat_id = ? AND threshold = ?", (chat_id, threshold))
        await db.execute("DELETE FROM group_notification_sent WHERE chat_id = ? AND threshold = ?", (chat_id, threshold))
        await db.commit()

async def mark_group_notification_sent(chat_id: int, threshold: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO group_notification_sent (chat_id, threshold) VALUES (?, ?)", (chat_id, threshold))
        await db.commit()

async def is_group_notification_sent(chat_id: int, threshold: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM group_notification_sent WHERE chat_id = ? AND threshold = ?", (chat_id, threshold))
        row = await cursor.fetchone()
        return row is not None