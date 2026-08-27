from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime

import discord
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import GuildMember, WorldCategory, WorldChannel, WorldRole
from world.repository import (
    replace_member_roles,
    upsert_category,
    upsert_channel,
    upsert_guild_world,
    upsert_member,
    upsert_role,
)

LOGGER = logging.getLogger(__name__)


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _channel_type(channel: discord.abc.GuildChannel) -> str:
    return str(channel.type)


def _category_id(channel: discord.abc.GuildChannel) -> int | None:
    category = getattr(channel, "category", None)
    return category.id if category is not None else None


def _parent_id(channel: discord.abc.GuildChannel) -> int | None:
    parent = getattr(channel, "parent", None)
    return parent.id if parent is not None else None


def _topic(channel: discord.abc.GuildChannel) -> str | None:
    return _text_or_none(getattr(channel, "topic", None))


def _position(channel: discord.abc.GuildChannel) -> int:
    return int(getattr(channel, "position", 0))


async def _iter_all_members(guild: discord.Guild) -> AsyncIterator[discord.Member]:
    # fetch_members() is used for a full authoritative member enumeration.
    # This requires the privileged GUILD_MEMBERS intent to be enabled.
    async for member in guild.fetch_members(limit=None):
        yield member


async def sync_guild_world(
    guild: discord.Guild,
    *,
    session_factory: async_sessionmaker[AsyncSession],
    fetch_members: bool = True,
) -> None:
    """Synchronise the factual Discord world into SQLite.

    Discord remains the authority. Existing world rows absent from this
    complete snapshot are marked inactive. Member removal is only inferred
    when a complete member enumeration has actually been performed.
    """
    async with session_factory() as session:
        await upsert_guild_world(
            session,
            guild_id=guild.id,
            name=guild.name,
            description=_text_or_none(getattr(guild, "description", None)),
        )

        category_ids = {category.id for category in guild.categories}
        for category in guild.categories:
            await upsert_category(
                session,
                guild_id=guild.id,
                category_id=category.id,
                name=category.name,
                position=category.position,
            )

        # Guild.channels contains guild channels other than category objects.
        # Active threads are added separately so the world can represent them
        # without replacing their parent channel.
        channels: dict[int, discord.abc.GuildChannel] = {channel.id: channel for channel in guild.channels}
        for thread in getattr(guild, "threads", []):
            channels[thread.id] = thread

        channel_ids = set(channels)
        for channel in channels.values():
            await upsert_channel(
                session,
                guild_id=guild.id,
                channel_id=channel.id,
                name=getattr(channel, "name", str(channel.id)),
                channel_type=_channel_type(channel),
                category_id=_category_id(channel),
                parent_id=_parent_id(channel),
                topic=_topic(channel),
                position=_position(channel),
            )

        role_ids = {role.id for role in guild.roles}
        for role in guild.roles:
            await upsert_role(
                session,
                guild_id=guild.id,
                role_id=role.id,
                name=role.name,
                position=role.position,
                managed=role.managed,
            )

        if fetch_members:
            seen_member_ids: set[int] = set()
            async for member in _iter_all_members(guild):
                seen_member_ids.add(member.id)
                joined_at: datetime | None = member.joined_at
                await upsert_member(
                    session,
                    guild_id=guild.id,
                    user_id=member.id,
                    display_name=member.display_name,
                    nickname=member.nick,
                    joined_at=joined_at,
                )
                # The everyone role is included by Discord in Member.roles.
                role_ids_for_member = [role.id for role in member.roles if role.id in role_ids]
                await replace_member_roles(
                    session,
                    guild_id=guild.id,
                    user_id=member.id,
                    role_ids=role_ids_for_member,
                )

            await session.execute(
                update(GuildMember)
                .where(
                    GuildMember.guild_id == guild.id,
                    GuildMember.user_discord_id.not_in(seen_member_ids),
                )
                .values(active=False)
            )

        # These are complete snapshots for categories/channels/roles from the
        # guild object, so rows missing from the snapshot can be marked inactive.
        if category_ids:
            await session.execute(
                update(WorldCategory)
                .where(
                    WorldCategory.guild_id == guild.id,
                    WorldCategory.category_id.not_in(category_ids),
                )
                .values(active=False)
            )
        else:
            await session.execute(
                update(WorldCategory)
                .where(WorldCategory.guild_id == guild.id)
                .values(active=False)
            )

        if channel_ids:
            await session.execute(
                update(WorldChannel)
                .where(
                    WorldChannel.guild_id == guild.id,
                    WorldChannel.channel_id.not_in(channel_ids),
                )
                .values(active=False)
            )
        else:
            await session.execute(
                update(WorldChannel)
                .where(WorldChannel.guild_id == guild.id)
                .values(active=False)
            )

        if role_ids:
            await session.execute(
                update(WorldRole)
                .where(
                    WorldRole.guild_id == guild.id,
                    WorldRole.role_id.not_in(role_ids),
                )
                .values(active=False)
            )
        else:
            await session.execute(
                update(WorldRole)
                .where(WorldRole.guild_id == guild.id)
                .values(active=False)
            )

        await session.commit()
        LOGGER.info(
            "World sync completed for guild %s (%s): %s categories, %s channels/threads, %s roles, members=%s",
            guild.id,
            guild.name,
            len(category_ids),
            len(channel_ids),
            len(role_ids),
            "full" if fetch_members else "skipped",
        )
