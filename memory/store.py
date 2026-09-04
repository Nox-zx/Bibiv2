from datetime import datetime, timezone
import logging

LOGGER = logging.getLogger(__name__)

MEMORY_KINDS = {
    "episodic", "semantic", "social", "relational", "autobiographical"
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def _columns(db):
    rows = await db.execute_fetchall('PRAGMA table_info("memories")')
    return {row[1] for row in rows}

async def remember(db, kind, content, *, guild_id=None, user_id=None, importance=0.5):
    if kind not in MEMORY_KINDS:
        return

    cols = await _columns(db)
    values = {}

    # v0.1 names
    aliases = {
        "kind": kind,
        "guild_id": guild_id,
        "user_id": user_id,
        "content": content[:1000],
        "importance": max(0, min(1, importance)),
        "created_at": now(),
        "last_recalled": None,
        "recall_count": 0,
    }

    # Common canonical/BP aliases
    if "owner_discord_id" in cols:
        aliases["owner_discord_id"] = user_id
    if "scope" in cols:
        aliases["scope"] = "user" if user_id is not None else "guild"
    if "channel_id" in cols:
        aliases["channel_id"] = None

    for c, v in aliases.items():
        if c in cols:
            values[c] = v

    if "content" not in values:
        raise RuntimeError("memories table has no content column")

    columns = ", ".join(f'"{k}"' for k in values)
    placeholders = ", ".join("?" for _ in values)
    await db.execute(
        f'INSERT INTO memories ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )
    await db.commit()

async def retrieve(db, query_terms: list[str], *, guild_id=None, user_id=None, limit=8):
    cols = await _columns(db)

    selected = [
        c for c in (
            "id", "kind", "content", "importance", "created_at",
            "last_recalled", "recall_count"
        ) if c in cols
    ]
    if "content" not in selected:
        return []

    conditions = []
    params = []

    if "guild_id" in cols:
        conditions.append("(guild_id IS NULL OR guild_id = ?)")
        params.append(guild_id)

    if "user_id" in cols:
        conditions.append("(user_id IS NULL OR user_id = ?)")
        params.append(user_id)
    elif "owner_discord_id" in cols:
        conditions.append("(owner_discord_id IS NULL OR owner_discord_id = ?)")
        params.append(user_id)

    where = " AND ".join(conditions) if conditions else "1=1"
    order_parts = []
    if "importance" in cols:
        order_parts.append("importance DESC")
    if "created_at" in cols:
        order_parts.append("created_at DESC")
    order = ", ".join(order_parts) or "rowid DESC"

    rows = await db.execute_fetchall(
        f'SELECT {", ".join(selected)} FROM memories '
        f'WHERE {where} ORDER BY {order} LIMIT 40',
        tuple(params),
    )

    terms = {t.lower() for t in query_terms if t}
    scored = []
    for r in rows:
        text = str(r["content"]).lower()
        overlap = sum(1 for t in terms if t in text)
        importance = float(r["importance"]) if "importance" in r.keys() else 0.5
        scored.append((overlap * 2 + importance, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = []

    for _, r in scored[:limit]:
        item = dict(r)
        result.append(item)

        if "id" in cols and "last_recalled" in cols and "recall_count" in cols:
            await db.execute(
                "UPDATE memories SET last_recalled=?, "
                "recall_count=recall_count+1 WHERE id=?",
                (now(), r["id"]),
            )

    await db.commit()
    return result
