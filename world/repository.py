from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    GuildMember,
    GuildMemberRole,
    GuildWorld,
    WorldCategory,
    WorldChannel,
    WorldRole,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def get_guild_world(session: AsyncSession, guild_id: int) -> GuildWorld | None:
    result = await session.execute(select(GuildWorld).where(GuildWorld.guild_id == guild_id))
    return result.scalar_one_or_none()


async def upsert_guild_world(
    session: AsyncSession,
    *,
    guild_id: int,
    name: str,
    description: str | None,
    active: bool = True,
) -> GuildWorld:
    row = await get_guild_world(session, guild_id)
    if row is None:
        row = GuildWorld(guild_id=guild_id)
        session.add(row)
    row.name = name
    row.description = description
    row.active = active
    row.updated_at = now_utc()
    await session.flush()
    return row


async def upsert_category(
    session: AsyncSession,
    *,
    guild_id: int,
    category_id: int,
    name: str,
    position: int,
) -> WorldCategory:
    result = await session.execute(
        select(WorldCategory).where(
            WorldCategory.guild_id == guild_id,
            WorldCategory.category_id == category_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = WorldCategory(guild_id=guild_id, category_id=category_id)
        session.add(row)
    row.name = name
    row.position = position
    row.active = True
    row.updated_at = now_utc()
    await session.flush()
    return row


async def upsert_channel(
    session: AsyncSession,
    *,
    guild_id: int,
    channel_id: int,
    name: str,
    channel_type: str,
    category_id: int | None,
    parent_id: int | None,
    topic: str | None,
    position: int,
) -> WorldChannel:
    result = await session.execute(
        select(WorldChannel).where(
            WorldChannel.guild_id == guild_id,
            WorldChannel.channel_id == channel_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = WorldChannel(guild_id=guild_id, channel_id=channel_id)
        session.add(row)
    row.name = name
    row.channel_type = channel_type
    row.category_id = category_id
    row.parent_id = parent_id
    row.topic = topic
    row.position = position
    row.active = True
    row.updated_at = now_utc()
    await session.flush()
    return row


async def upsert_role(
    session: AsyncSession,
    *,
    guild_id: int,
    role_id: int,
    name: str,
    position: int,
    managed: bool,
) -> WorldRole:
    result = await session.execute(
        select(WorldRole).where(
            WorldRole.guild_id == guild_id,
            WorldRole.role_id == role_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = WorldRole(guild_id=guild_id, role_id=role_id)
        session.add(row)
    row.name = name
    row.position = position
    row.managed = managed
    row.active = True
    row.updated_at = now_utc()
    await session.flush()
    return row


async def upsert_member(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    display_name: str,
    nickname: str | None,
    joined_at: datetime | None,
) -> GuildMember:
    result = await session.execute(
        select(GuildMember).where(
            GuildMember.guild_id == guild_id,
            GuildMember.user_discord_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = GuildMember(guild_id=guild_id, user_discord_id=user_id)
        session.add(row)
    row.display_name = display_name
    row.nickname = nickname
    row.joined_at = joined_at
    row.active = True
    row.updated_at = now_utc()
    await session.flush()
    return row


async def replace_member_roles(
    session: AsyncSession,
    *,
    guild_id: int,
    user_id: int,
    role_ids: list[int],
) -> None:
    await session.execute(
        delete(GuildMemberRole).where(
            GuildMemberRole.guild_id == guild_id,
            GuildMemberRole.user_discord_id == user_id,
        )
    )
    for role_id in role_ids:
        session.add(
            GuildMemberRole(
                guild_id=guild_id,
                user_discord_id=user_id,
                role_id=role_id,
            )
        )
    await session.flush()
