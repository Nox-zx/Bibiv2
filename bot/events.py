from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

import discord
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ai_core.gateway import GeminiQuotaExceeded, GeminiTemporarilyUnavailable
from database.models import ChannelState, MessageRecord
from database.repositories import get_or_create_channel_state, get_or_create_user
from mind.context import build_cognitive_context
from mind.perception import Perception
from safety.guard import SafetyGuard

LOGGER = logging.getLogger(__name__)

# Prevent a quota/failure fallback from becoming spam when a channel is active.
_FALLBACK_COOLDOWN_SECONDS = 300
_fallback_sent_at: dict[int, datetime] = {}


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _should_fallback(channel_id: int) -> bool:
    now = datetime.now(timezone.utc)
    previous = _fallback_sent_at.get(channel_id)
    if previous and (now - previous).total_seconds() < _FALLBACK_COOLDOWN_SECONDS:
        return False
    _fallback_sent_at[channel_id] = now
    return True


async def handle_message(
    message: discord.Message,
    *,
    bot_user_id: int,
    session_factory: async_sessionmaker[AsyncSession],
    cognitive_mind,
    attention_minutes: int,
    max_response_length: int,
) -> None:
    if message.author.bot:
        return

    is_reply = bool(message.reference and message.reference.message_id)
    mentioned = bot_user_id in {member.id for member in message.mentions}

    replied_content = None
    if is_reply and message.reference and isinstance(message.reference.resolved, discord.Message):
        replied_content = message.reference.resolved.content

    recent_messages = []
    async for item in message.channel.history(limit=25):
        if item.id == message.id:
            continue
        recent_messages.append({
            "author_id": item.author.id,
            "author_name": item.author.display_name,
            "content": item.content,
        })
    recent_messages.reverse()

    perception = Perception(
        message_id=message.id,
        guild_id=message.guild.id if message.guild else None,
        channel_id=message.channel.id,
        author_id=message.author.id,
        author_name=message.author.display_name,
        content=message.content,
        timestamp=datetime.now(timezone.utc),
        is_reply=is_reply,
        mentioned_bibi=mentioned,
        replied_message_content=replied_content,
        recent_messages=recent_messages,
    )

    async with session_factory() as session:
        await get_or_create_user(session, message.author.id, message.author.display_name)
        if message.guild:
            state = await get_or_create_channel_state(session, message.guild.id, message.channel.id)
            if mentioned or is_reply:
                state.attention_until = datetime.now(timezone.utc) + timedelta(minutes=attention_minutes)

        session.add(
            MessageRecord(
                discord_message_id=message.id,
                guild_id=message.guild.id if message.guild else None,
                channel_id=message.channel.id,
                author_discord_id=message.author.id,
                content=message.content,
                is_reply=is_reply,
                mentioned_bibi=mentioned,
            )
        )

        attention_state = "inactive"
        if message.guild:
            state = await get_or_create_channel_state(session, message.guild.id, message.channel.id)
            attention_until = _as_utc(state.attention_until)
            if attention_until and attention_until > datetime.now(timezone.utc):
                attention_state = "engaged" if (mentioned or is_reply) else "aware"

        context = await build_cognitive_context(session, perception, attention_state=attention_state)
        try:
            decision = await cognitive_mind.decide(context)
        except GeminiQuotaExceeded:
            LOGGER.warning(
                "Gemini daily quota exhausted; skipping cognitive response for message %s",
                message.id,
            )
            if (mentioned or is_reply) and _should_fallback(message.channel.id):
                await message.reply(
                    "tô sem cérebro por agora kkkk tenta falar comigo mais tarde",
                    mention_author=False,
                )
            await session.commit()
            return
        except GeminiTemporarilyUnavailable:
            LOGGER.exception("Gemini temporarily unavailable for message %s", message.id)
            if (mentioned or is_reply) and _should_fallback(message.channel.id):
                await message.reply(
                    "pera aí, meu cérebro deu uma engasgada kkkk",
                    mention_author=False,
                )
            await session.commit()
            return
        except Exception:
            LOGGER.exception("Cognitive call failed for message %s", message.id)
            await session.commit()
            return

        decision = SafetyGuard().validate_cognitive(decision)

        if decision.participation in {"respond", "ask_clarification"} and decision.response:
            content = decision.response[:max_response_length]
            await message.reply(content, mention_author=False)

        # Memory candidates are deliberately persisted only after the response path completes.
        from memory.manager import persist_memory_candidates
        await persist_memory_candidates(
            session,
            decision.memory_candidates,
            guild_id=message.guild.id if message.guild else None,
            channel_id=message.channel.id,
        )

        await session.commit()