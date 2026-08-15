from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import get_relevant_memories


async def retrieve_memories(
    session: AsyncSession,
    *,
    guild_id: int | None,
    channel_id: int,
    author_id: int,
    limit: int = 12,
) -> list[dict]:
    memories = await get_relevant_memories(
        session,
        guild_id=guild_id,
        channel_id=channel_id,
        author_id=author_id,
        limit=limit,
    )
    return [
        {
            "id": memory.id,
            "kind": memory.kind,
            "scope": memory.scope,
            "content": memory.content,
            "importance": memory.importance,
            "confidence": memory.confidence,
            "source": memory.source,
            "owner_discord_id": memory.owner_discord_id,
        }
        for memory in memories
    ]
