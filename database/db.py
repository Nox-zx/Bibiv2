from pathlib import Path
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER UNIQUE,
    guild_id INTEGER,
    channel_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_direct INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    guild_id INTEGER,
    user_id INTEGER,
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL,
    last_recalled TEXT,
    recall_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS relationships (
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    familiarity REAL NOT NULL DEFAULT 0,
    trust REAL NOT NULL DEFAULT 0.5,
    closeness REAL NOT NULL DEFAULT 0,
    impression TEXT NOT NULL DEFAULT '',
    last_interaction TEXT,
    PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS channel_state (
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    last_activity TEXT,
    attention_until TEXT,
    last_bibi_message TEXT,
    PRIMARY KEY (guild_id, channel_id)
);
CREATE TABLE IF NOT EXISTS self_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    mood TEXT NOT NULL DEFAULT 'neutral',
    energy REAL NOT NULL DEFAULT 0.7,
    sociability REAL NOT NULL DEFAULT 0.6,
    curiosity REAL NOT NULL DEFAULT 0.5,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    due_at TEXT NOT NULL,
    text TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0
);
"""

async def connect(path: str) -> aiosqlite.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.executescript(SCHEMA)
    await db.commit()
    return db


async def fetchone(db, sql, params=()):
    cursor = await db.execute(sql, params)
    try:
        return await cursor.fetchone()
    finally:
        await cursor.close()
