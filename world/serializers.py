from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import GuildMember, GuildMemberRole, GuildWorld, WorldCategory, WorldChannel, WorldRole


async def serialize_guild_world(session: AsyncSession, guild_id: int) -> dict:
    guild = (
        await session.execute(
            select(GuildWorld).where(GuildWorld.guild_id == guild_id, GuildWorld.active.is_(True))
        )
    ).scalar_one_or_none()
    if guild is None:
        return {"guild": None, "categories": [], "channels": [], "roles": [], "members": []}

    categories = list(
        (await session.execute(
            select(WorldCategory)
            .where(WorldCategory.guild_id == guild_id, WorldCategory.active.is_(True))
            .order_by(WorldCategory.position)
        )).scalars()
    )
    channels = list(
        (await session.execute(
            select(WorldChannel)
            .where(WorldChannel.guild_id == guild_id, WorldChannel.active.is_(True))
            .order_by(WorldChannel.position)
        )).scalars()
    )
    roles = list(
        (await session.execute(
            select(WorldRole)
            .where(WorldRole.guild_id == guild_id, WorldRole.active.is_(True))
            .order_by(WorldRole.position.desc())
        )).scalars()
    )
    members = list(
        (await session.execute(
            select(GuildMember)
            .where(GuildMember.guild_id == guild_id, GuildMember.active.is_(True))
            .order_by(GuildMember.display_name)
        )).scalars()
    )
    role_links = list(
        (await session.execute(
            select(GuildMemberRole).where(GuildMemberRole.guild_id == guild_id)
        )).scalars()
    )
    roles_by_member: dict[int, list[int]] = {}
    for link in role_links:
        roles_by_member.setdefault(link.user_discord_id, []).append(link.role_id)

    return {
        "guild": {
            "id": guild.guild_id,
            "name": guild.name,
            "description": guild.description,
        },
        "categories": [
            {"id": item.category_id, "name": item.name, "position": item.position}
            for item in categories
        ],
        "channels": [
            {
                "id": item.channel_id,
                "name": item.name,
                "type": item.channel_type,
                "category_id": item.category_id,
                "parent_id": item.parent_id,
                "topic": item.topic,
                "position": item.position,
            }
            for item in channels
        ],
        "roles": [
            {
                "id": item.role_id,
                "name": item.name,
                "position": item.position,
                "managed": item.managed,
            }
            for item in roles
        ],
        "members": [
            {
                "user_id": item.user_discord_id,
                "display_name": item.display_name,
                "nickname": item.nickname,
                "joined_at": item.joined_at.isoformat() if item.joined_at else None,
                "role_ids": roles_by_member.get(item.user_discord_id, []),
            }
            for item in members
        ],
    }
