from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ai_core.schemas import MemoryCandidate
from database.models import Memory


async def persist_memory_candidates(
    session: AsyncSession,
    candidates: list[MemoryCandidate],
    *,
    guild_id: int | None,
    channel_id: int | None,
) -> None:
    for candidate in candidates:
        if candidate.scope == "user_private" and candidate.owner_discord_id is None:
            continue
        session.add(
            Memory(
                owner_discord_id=candidate.owner_discord_id,
                guild_id=guild_id,
                channel_id=channel_id if candidate.scope in {"channel", "public"} else None,
                kind=candidate.kind,
                scope=candidate.scope,
                content=candidate.content,
                importance=candidate.importance,
                confidence=candidate.confidence,
                source="conversation",
            )
        )
