from __future__ import annotations

from ai_core.schemas import ReflectionResult
from database.models import Memory
from sqlalchemy.ext.asyncio import AsyncSession


async def apply_reflection_memory_updates(
    session: AsyncSession,
    result: ReflectionResult,
    *,
    guild_id: int | None,
) -> None:
    for candidate in result.memory_updates:
        session.add(
            Memory(
                owner_discord_id=candidate.owner_discord_id,
                guild_id=guild_id,
                channel_id=None,
                kind=candidate.kind,
                scope=candidate.scope,
                content=candidate.content,
                importance=candidate.importance,
                confidence=candidate.confidence,
                source="reflection",
            )
        )
