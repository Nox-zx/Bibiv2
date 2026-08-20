from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(slots=True)
class WorldContext:
    """Factual snapshot of the Discord environment for the current message.

    Everything here is read directly from discord.py objects. It must never
    be guessed, inferred, or reconstructed by the cognitive mind — Bibi's
    world model is grounded in what Python actually observes.
    """

    guild_name: str | None
    channel_id: int
    channel_name: str | None
    channel_topic: str | None
    channel_type: str
    category_name: str | None
    is_dm: bool
    recent_active_members: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "guild_name": self.guild_name,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_topic": self.channel_topic,
            "channel_type": self.channel_type,
            "category_name": self.category_name,
            "is_dm": self.is_dm,
            "recent_active_members": self.recent_active_members,
        }


def build_world_context(
    message: discord.Message,
    *,
    recent_messages: list[dict],
) -> WorldContext:
    """Build a WorldContext strictly from the discord.Message and the already
    fetched recent_messages (no extra API calls beyond what perception uses).
    """
    channel = message.channel
    guild = message.guild

    is_dm = guild is None

    channel_name = getattr(channel, "name", None)
    channel_topic = getattr(channel, "topic", None)
    category = getattr(channel, "category", None)
    category_name = getattr(category, "name", None) if category else None
    channel_type = str(getattr(channel, "type", "unknown"))

    # Distinct recent participants, most-recent-first, excluding Bibi's own author id
    # is not knowable here (bot filters itself upstream); this is purely factual tally.
    seen: dict[int, dict] = {}
    for item in recent_messages:
        author_id = item.get("author_id")
        if author_id is None or author_id in seen:
            continue
        seen[author_id] = {
            "author_id": author_id,
            "author_name": item.get("author_name"),
        }
    recent_active_members = list(seen.values())[:10]

    return WorldContext(
        guild_name=guild.name if guild else None,
        channel_id=channel.id,
        channel_name=channel_name,
        channel_topic=channel_topic,
        channel_type=channel_type,
        category_name=category_name,
        is_dm=is_dm,
        recent_active_members=recent_active_members,
    )
