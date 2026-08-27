from __future__ import annotations

import logging

import discord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from world.repository import (
    replace_member_roles,
    upsert_category,
    upsert_channel,
    upsert_guild_world,
    upsert_member,
    upsert_role,
)

LOGGER = logging.getLogger(__name__)


def _text(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _category_id(channel: discord.abc.GuildChannel) -> int | None:
    category = getattr(channel, "category", None)
    return category.id if category else None


def _parent_id(channel: discord.abc.GuildChannel) -> int | None:
    parent = getattr(channel, "parent", None)
    return parent.id if parent else None


async def sync_guild_event(
    guild: discord.Guild,
    *,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        await upsert_guild_world(
            session,
            guild_id=guild.id,
            name=guild.name,
            description=_text(guild.description),
        )
        await session.commit()


async def sync_channel_event(
    channel: discord.abc.GuildChannel,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    active: bool = True,
) -> None:
    if channel.guild is None:
        return
    async with session_factory() as session:
        if active:
            await upsert_channel(
                session,
                guild_id=channel.guild.id,
                channel_id=channel.id,
                name=channel.name,
                channel_type=str(channel.type),
                category_id=_category_id(channel),
                parent_id=_parent_id(channel),
                topic=_text(getattr(channel, "topic", None)),
                position=int(getattr(channel, "position", 0)),
            )
        else:
            from sqlalchemy import update
            from database.models import WorldChannel
            await session.execute(
                update(WorldChannel)
                .where(
                    WorldChannel.guild_id == channel.guild.id,
                    WorldChannel.channel_id == channel.id,
                )
                .values(active=False)
            )
        await session.commit()


async def sync_role_event(
    role: discord.Role,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    active: bool = True,
) -> None:
    async with session_factory() as session:
        if active:
            await upsert_role(
                session,
                guild_id=role.guild.id,
                role_id=role.id,
                name=role.name,
                position=role.position,
                managed=role.managed,
            )
        else:
            from sqlalchemy import update
            from database.models import WorldRole
            await session.execute(
                update(WorldRole)
                .where(WorldRole.guild_id == role.guild.id, WorldRole.role_id == role.id)
                .values(active=False)
            )
        await session.commit()


async def sync_member_event(
    member: discord.Member,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    active: bool = True,
) -> None:
    async with session_factory() as session:
        if active:
            await upsert_member(
                session,
                guild_id=member.guild.id,
                user_id=member.id,
                display_name=member.display_name,
                nickname=member.nick,
                joined_at=member.joined_at,
            )
            await replace_member_roles(
                session,
                guild_id=member.guild.id,
                user_id=member.id,
                role_ids=[role.id for role in member.roles],
            )
        else:
            from sqlalchemy import update
            from database.models import GuildMember
            await session.execute(
                update(GuildMember)
                .where(
                    GuildMember.guild_id == member.guild.id,
                    GuildMember.user_discord_id == member.id,
                )
                .values(active=False)
            )
        await session.commit()
