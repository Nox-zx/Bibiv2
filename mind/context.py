from __future__ import annotations

from database.repositories import (
    get_relationship,
    get_self_model,
    get_or_create_channel_state,
)
from memory.retrieval import retrieve_memories
from mind.perception import Perception
from mind.attention import Attention
from mind.contracts import CognitiveContext
from utils.time_context import get_time_context
from sqlalchemy.ext.asyncio import AsyncSession


async def build_cognitive_context(
    session: AsyncSession,
    perception: Perception,
    *,
    attention_state: str,
) -> dict:
    relationship = None
    self_model = await get_self_model(session)

    if perception.guild_id is not None:
        relationship = await get_relationship(
            session,
            perception.guild_id,
            perception.author_id,
        )
        await get_or_create_channel_state(
            session,
            perception.guild_id,
            perception.channel_id,
        )

    memories = await retrieve_memories(
        session,
        guild_id=perception.guild_id,
        channel_id=perception.channel_id,
        author_id=perception.author_id,
    )

    attention = Attention().decide(
        perception,
        attention_state=attention_state,
    )

    # v0.1 keeps the world representation factual and intentionally small.
    # More complete server/world modelling belongs to v0.2.
    world = {
        "guild_id": perception.guild_id,
        "channel_id": perception.channel_id,
        "channel_known": perception.guild_id is not None,
    }

    context = CognitiveContext(
        perception=perception.as_dict(),
        world=world,
        attention=attention,
        time_context=get_time_context(),
        relationship={
            "familiarity": relationship.familiarity,
            "trust": relationship.trust,
            "closeness": relationship.closeness,
            "impression": relationship.impression,
        } if relationship else None,
        self_model={
            "base": self_model.base_state,
            "evolved": self_model.evolved_state,
            "version": self_model.version,
        },
        memories=memories,
        internal_state={
            "emotional_state": None,
            "active_drives": [],
            "curiosities": [],
        },
    )

    return context.as_dict()
