from datetime import datetime, timezone
import aiosqlite

MEMORY_KINDS = {
    "episodic", "semantic", "social", "relational", "autobiographical"
}

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def remember(db, kind, content, *, guild_id=None, user_id=None, importance=0.5):
    if kind not in MEMORY_KINDS:
        return
    await db.execute(
        """INSERT INTO memories(kind,guild_id,user_id,content,importance,created_at)
           VALUES(?,?,?,?,?,?)""",
        (kind, guild_id, user_id, content[:1000], max(0, min(1, importance)), now()),
    )
    await db.commit()

async def retrieve(db, query_terms: list[str], *, guild_id=None, user_id=None, limit=8):
    rows = await db.execute_fetchall(
        """SELECT id,kind,content,importance,created_at,last_recalled,recall_count
           FROM memories
           WHERE (guild_id IS NULL OR guild_id = ?)
             AND (user_id IS NULL OR user_id = ?)
           ORDER BY importance DESC, created_at DESC
           LIMIT 40""",
        (guild_id, user_id),
    )
    terms = {t.lower() for t in query_terms if t}
    scored=[]
    for r in rows:
        text=r["content"].lower()
        overlap=sum(1 for t in terms if t in text)
        score=overlap*2+r["importance"]
        scored.append((score,r))
    scored.sort(key=lambda x:x[0], reverse=True)
    result=[]
    for _,r in scored[:limit]:
        result.append(dict(r))
        await db.execute(
            "UPDATE memories SET last_recalled=?, recall_count=recall_count+1 WHERE id=?",
            (now(), r["id"])
        )
    await db.commit()
    return result
