from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

LOGGER = logging.getLogger(__name__)

# This is the schema expected by Bibi v0.1.x.
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

# Columns required by the current v0.1 runtime.  Existing databases from
# older Bibi builds are migrated in place instead of being deleted.
REQUIRED_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "id": "INTEGER",
        "name": "TEXT",
        "first_seen": "TEXT",
        "last_seen": "TEXT",
        "message_count": "INTEGER DEFAULT 0",
    },
    "messages": {
        # Intentionally nullable: old rows cannot safely be assumed to have
        # stored a Discord message ID in their old primary-key column.
        "discord_id": "INTEGER",
        "guild_id": "INTEGER",
        "channel_id": "INTEGER",
        "author_id": "INTEGER",
        "content": "TEXT",
        "created_at": "TEXT",
        "is_direct": "INTEGER DEFAULT 0",
    },
    "memories": {
        "kind": "TEXT",
        "guild_id": "INTEGER",
        "user_id": "INTEGER",
        "content": "TEXT",
        "importance": "REAL DEFAULT 0.5",
        "created_at": "TEXT",
        "last_recalled": "TEXT",
        "recall_count": "INTEGER DEFAULT 0",
    },
    "relationships": {
        "guild_id": "INTEGER",
        "user_id": "INTEGER",
        "familiarity": "REAL DEFAULT 0",
        "trust": "REAL DEFAULT 0.5",
        "closeness": "REAL DEFAULT 0",
        "impression": "TEXT DEFAULT ''",
        "last_interaction": "TEXT",
    },
    "channel_state": {
        "guild_id": "INTEGER",
        "channel_id": "INTEGER",
        "last_activity": "TEXT",
        "attention_until": "TEXT",
        "last_bibi_message": "TEXT",
    },
    "self_state": {
        "id": "INTEGER",
        "mood": "TEXT DEFAULT 'neutral'",
        "energy": "REAL DEFAULT 0.7",
        "sociability": "REAL DEFAULT 0.6",
        "curiosity": "REAL DEFAULT 0.5",
        "updated_at": "TEXT",
    },
    "reminders": {
        "user_id": "INTEGER",
        "channel_id": "INTEGER",
        "due_at": "TEXT",
        "text": "TEXT",
        "delivered": "INTEGER DEFAULT 0",
    },
}


def _quote_identifier(value: str) -> str:
    """Quote a SQLite identifier safely."""
    return '"' + value.replace('"', '""') + '"'


async def _table_exists(db: aiosqlite.Connection, table: str) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    )
    try:
        return await cursor.fetchone() is not None
    finally:
        await cursor.close()


async def _table_columns(db: aiosqlite.Connection, table: str) -> set[str]:
    cursor = await db.execute(f"PRAGMA table_info({_quote_identifier(table)})")
    try:
        rows = await cursor.fetchall()
    finally:
        await cursor.close()
    return {row[1] for row in rows}


async def _migrate_existing_table(
    db: aiosqlite.Connection,
    table: str,
    required: dict[str, str],
) -> list[str]:
    """Add only missing columns; never rebuild or delete an existing table."""
    if not await _table_exists(db, table):
        return []

    existing = await _table_columns(db, table)
    added: list[str] = []

    for column, definition in required.items():
        if column in existing:
            continue

        # SQLite allows ALTER TABLE ADD COLUMN for nullable columns and for
        # columns with constant defaults. We deliberately avoid NOT NULL here
        # because legacy rows may not have a meaningful value.
        sql = (
            f"ALTER TABLE {_quote_identifier(table)} "
            f"ADD COLUMN {_quote_identifier(column)} {definition}"
        )
        await db.execute(sql)
        added.append(column)

    return added


async def _migrate_legacy_database(db: aiosqlite.Connection) -> None:
    """Bring older Bibi SQLite databases up to the v0.1 runtime contract.

    The important property is non-destructive migration: existing tables and
    rows remain in place. We only add missing schema pieces required by the
    current runtime.
    """
    changes: list[str] = []

    for table, required in REQUIRED_COLUMNS.items():
        added = await _migrate_existing_table(db, table, required)
        if added:
            changes.append(f"{table}: +{', '.join(added)}")

    # New tables are created by SCHEMA below. For existing messages, do not
    # invent Discord IDs by copying the SQLite row id: those values may belong
    # to a completely different legacy identifier space.
    if changes:
        LOGGER.info("Database migration applied: %s", "; ".join(changes))

    # A non-unique index is safe even when legacy data contains duplicate or
    # NULL values. New Discord message IDs are still usable by the runtime.
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_discord_id "
        "ON messages(discord_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_channel_id "
        "ON messages(channel_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_author_id "
        "ON messages(author_id)"
    )


async def connect(path: str) -> aiosqlite.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row

    try:
        # First create anything that does not exist, then migrate tables that
        # already existed under an older Bibi schema.
        await db.executescript(SCHEMA)
        await _migrate_legacy_database(db)
        await db.commit()
    except Exception:
        await db.rollback()
        await db.close()
        raise

    return db


async def fetchone(db: aiosqlite.Connection, sql: str, params=()):
    cursor = await db.execute(sql, params)
    try:
        return await cursor.fetchone()
    finally:
        await cursor.close()