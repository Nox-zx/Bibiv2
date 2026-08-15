from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Memory


async def forget_memory_ids(session: AsyncSession, memory_ids: list[int]) -> None:
    if not memory_ids:
        return
    result = await session.execute(select(Memory).where(Memory.id.in_(memory_ids)))
    for memory in result.scalars():
        if memory.importance != "permanent":
            memory.active = False
