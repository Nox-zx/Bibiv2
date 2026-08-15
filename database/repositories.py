from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ChannelState, Memory, Relationship, SelfModel, User


async def get_or_create_user(session: AsyncSession, discord_id: int, display_name: str) -> User:
    result = await session.execute(select(User).where(User.discord_id == discord_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(discord_id=discord_id, display_name=display_name)
        session.add(user)
    else:
        user.display_name = display_name
        user.last_seen_at = datetime.now(timezone.utc)
    await session.flush()
    return user


async def get_or_create_channel_state(session: AsyncSession, guild_id: int, channel_id: int) -> ChannelState:
    result = await session.execute(select(ChannelState).where(ChannelState.channel_id == channel_id))
    state = result.scalar_one_or_none()
    if state is None:
        state = ChannelState(guild_id=guild_id, channel_id=channel_id)
        session.add(state)
        await session.flush()
    return state


async def get_relevant_memories(
    session: AsyncSession,
    *,
    guild_id: int | None,
    channel_id: int,
    author_id: int,
    limit: int = 12,
) -> list[Memory]:
    result = await session.execute(
        select(Memory)
        .where(Memory.active.is_(True))
        .where((Memory.guild_id == guild_id) | (Memory.guild_id.is_(None)))
        .where((Memory.channel_id == channel_id) | (Memory.channel_id.is_(None)))
        .where((Memory.owner_discord_id == author_id) | (Memory.owner_discord_id.is_(None)))
        .order_by(Memory.importance.desc(), Memory.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_relationship(session: AsyncSession, guild_id: int, user_id: int) -> Relationship | None:
    result = await session.execute(
        select(Relationship).where(
            Relationship.guild_id == guild_id,
            Relationship.user_discord_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_self_model(session: AsyncSession) -> SelfModel:
    result = await session.execute(select(SelfModel).where(SelfModel.id == 1))
    model = result.scalar_one_or_none()
    if model is None:
        model = SelfModel(id=1)
        session.add(model)
        await session.flush()
    return model
