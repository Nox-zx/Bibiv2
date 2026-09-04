from pathlib import Path
import logging
import aiosqlite

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    discord_id INTEGER UNIQUE,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER,
    familiarity REAL NOT NULL DEFAULT 0,
    trust REAL NOT NULL DEFAULT 0.5,
    closeness REAL NOT NULL DEFAULT 0,
    impression TEXT NOT NULL DEFAULT '',
    last_interaction TEXT
);

CREATE TABLE IF NOT EXISTS channel_state (
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    last_activity TEXT,
    attention_until TEXT,
    last_bibi_message TEXT
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

# Columns that the v0.1 runtime may need on older databases.
# They are deliberately nullable/defaulted so SQLite can add them safely.
MIGRATIONS = {
    "users": {
        "name": "TEXT",
        "first_seen": "TEXT",
        "last_seen": "TEXT",
        "message_count": "INTEGER NOT NULL DEFAULT 0",
        "discord_id": "INTEGER",
    },
    "messages": {
        "discord_id": "INTEGER",
        "guild_id": "INTEGER",
        "channel_id": "INTEGER",
        "author_id": "INTEGER",
        "content": "TEXT",
        "created_at": "TEXT",
        "is_direct": "INTEGER NOT NULL DEFAULT 0",
    },
    "memories": {
        "kind": "TEXT",
        "guild_id": "INTEGER",
        "user_id": "INTEGER",
        "content": "TEXT",
        "importance": "REAL NOT NULL DEFAULT 0.5",
        "created_at": "TEXT",
        "last_recalled": "TEXT",
        "recall_count": "INTEGER NOT NULL DEFAULT 0",
    },
    "relationships": {
        "guild_id": "INTEGER",
        "user_id": "INTEGER",
        "user_discord_id": "INTEGER",
        "familiarity": "REAL NOT NULL DEFAULT 0",
        "trust": "REAL NOT NULL DEFAULT 0.5",
        "closeness": "REAL NOT NULL DEFAULT 0",
        "impression": "TEXT NOT NULL DEFAULT ''",
        "last_interaction": "TEXT",
        "updated_at": "TEXT",
    },
    "channel_state": {
        "guild_id": "INTEGER",
        "channel_id": "INTEGER",
        "last_activity": "TEXT",
        "attention_until": "TEXT",
        "last_bibi_message": "TEXT",
    },
}

async def table_columns(db, table: str) -> set[str]:
    rows = await db.execute_fetchall(f'PRAGMA table_info("{table}")')
    return {row[1] for row in rows}

async def _migrate(db):
    for table, columns in MIGRATIONS.items():
        existing = await table_columns(db, table)
        for name, definition in columns.items():
            if name not in existing:
                try:
                    await db.execute(
                        f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}'
                    )
                    log.info("Database migration: %s.%s added", table, name)
                except Exception:
                    log.exception("Failed adding database column %s.%s", table, name)

    # Safe indexes only. Do not add uniqueness constraints to legacy tables:
    # their existing data may contain duplicates.
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_discord_id ON messages(discord_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_author_id ON messages(author_id)",
        "CREATE INDEX IF NOT EXISTS idx_relationships_user_id ON relationships(guild_id,user_id)",
        "CREATE INDEX IF NOT EXISTS idx_relationships_user_discord_id ON relationships(guild_id,user_discord_id)",
        "CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(guild_id,user_id)",
        "CREATE INDEX IF NOT EXISTS idx_channel_state_key ON channel_state(guild_id,channel_id)",
    ):
        try:
            await db.execute(sql)
        except Exception:
            log.exception("Failed creating compatibility index")

async def connect(path: str) -> aiosqlite.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    try:
        await db.executescript(SCHEMA)
        await _migrate(db)
        await db.commit()
        return db
    except Exception:
        await db.rollback()
        await db.close()
        raise

async def fetchone(db, sql, params=()):
    cursor = await db.execute(sql, params)
    try:
        return await cursor.fetchone()
    finally:
        await cursor.close()
