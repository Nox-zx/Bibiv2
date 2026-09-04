import logging
from datetime import datetime, timezone, timedelta

import discord

from mind.perception import Perception
from mind.attention import Attention
from mind.world import build_world
from mind.self_model import SELF_MODEL
from mind.contracts import CognitiveContext
from mind.emotion import EmotionalState, time_adjustment
from memory.store import retrieve, remember
from database.db import fetchone, table_columns

LOGGER = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(self, bot):
        self.bot = bot
        self.attention = Attention()
        self.emotion = EmotionalState()

    async def process(self, message: discord.Message):
        try:
            await self._process(message)
        except Exception:
            # Never let one malformed/legacy database row kill on_message.
            LOGGER.exception(
                "Unhandled message processing failure: message_id=%s channel_id=%s",
                message.id,
                message.channel.id,
            )

    async def _process(self, message: discord.Message):
        recent = []
        async for m in message.channel.history(limit=20, before=message):
            recent.append({
                "author": m.author.display_name,
                "author_id": m.author.id,
                "content": m.content,
                "time": m.created_at.isoformat(),
            })
        recent.reverse()

        direct = self._direct(message)
        reply = self._reply_to_bibi(message)
        state = await self._channel_engagement(message)

        attention = self.attention.decide(
            direct=direct,
            reply=reply,
            engaged=state,
            ambient_relevance=False,
        )

        if not attention.attend:
            await self._record(message, direct)
            return

        world = build_world(message.guild, message.channel, recent)
        temporal = time_adjustment(world["hour"])
        self.emotion.energy = max(
            0, min(1, self.emotion.energy + temporal["energy"])
        )
        self.emotion.sociability = max(
            0, min(1, self.emotion.sociability + temporal["sociability"])
        )

        relationship = await self._relationship(message)
        terms = message.content.replace("?", " ").split()[:12]
        memories = await retrieve(
            self.bot.db,
            terms,
            guild_id=message.guild.id if message.guild else None,
            user_id=message.author.id,
        )

        context = CognitiveContext(
            self_model=SELF_MODEL,
            emotional_state=self.emotion.as_dict(),
            world=world,
            perception=Perception(
                message_id=message.id,
                guild_id=message.guild.id if message.guild else None,
                channel_id=message.channel.id,
                author_id=message.author.id,
                author_name=message.author.display_name,
                content=message.content,
                created_at=message.created_at,
                direct_address=direct,
                reply_to_bibi=reply,
                recent_messages=recent,
            ).as_dict(),
            attention=attention.__dict__,
            relationship=relationship,
            memories=memories,
            conversation=recent,
            temporal_context=temporal,
        )

        try:
            decision = await self.bot.cognitive.decide(context.as_dict())
        except Exception:
            LOGGER.exception(
                "Cognitive processing failed: message_id=%s channel_id=%s",
                message.id,
                message.channel.id,
            )
            await self._record(message, direct)
            return

        await self._record(message, direct)

        if decision.memory_candidates:
            for mem in decision.memory_candidates:
                await remember(
                    self.bot.db,
                    mem.kind,
                    mem.content,
                    guild_id=message.guild.id if message.guild else None,
                    user_id=mem.user_id or message.author.id,
                    importance=mem.importance,
                )

        self._apply_emotion(decision.emotion)

        if decision.should_respond and decision.response:
            text = decision.response.strip()[:1200]
            if text:
                await message.reply(text, mention_author=False)
                await self._set_channel_attention(message)

    def _direct(self, message):
        if self.bot.user and self.bot.user.mentioned_in(message):
            return True
        lowered = message.content.lower().strip()
        return any(
            lowered.startswith(x)
            for x in ("bibi ", "bibi,", "bibi:")
        )

    def _reply_to_bibi(self, message):
        ref = message.reference
        return bool(
            ref
            and ref.resolved
            and getattr(ref.resolved, "author", None) == self.bot.user
        )

    async def _channel_engagement(self, message):
        if not message.guild:
            return False
        row = await fetchone(
            self.bot.db,
            "SELECT attention_until FROM channel_state "
            "WHERE guild_id=? AND channel_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (message.guild.id, message.channel.id),
        )
        if not row or not row["attention_until"]:
            return False
        try:
            return datetime.fromisoformat(
                row["attention_until"]
            ) > datetime.now(timezone.utc)
        except (TypeError, ValueError):
            return False

    async def _set_channel_attention(self, message):
        if not message.guild:
            return

        now = datetime.now(timezone.utc)
        until = (now + timedelta(minutes=20)).isoformat()
        cols = await table_columns(self.bot.db, "channel_state")

        # Prefer an existing row. This avoids relying on a legacy PRIMARY KEY
        # or UNIQUE constraint that may not exist.
        row = await fetchone(
            self.bot.db,
            "SELECT rowid FROM channel_state "
            "WHERE guild_id=? AND channel_id=? ORDER BY rowid DESC LIMIT 1",
            (message.guild.id, message.channel.id),
        )

        values = {}
        if "guild_id" in cols:
            values["guild_id"] = message.guild.id
        if "channel_id" in cols:
            values["channel_id"] = message.channel.id
        if "attention_until" in cols:
            values["attention_until"] = until
        if "last_bibi_message" in cols:
            values["last_bibi_message"] = now.isoformat()

        if not values:
            return

        if row:
            assignments = ", ".join(f'"{k}"=?' for k in values if k not in ("guild_id", "channel_id"))
            params = [values[k] for k in values if k not in ("guild_id", "channel_id")]
            if assignments:
                await self.bot.db.execute(
                    f"UPDATE channel_state SET {assignments} WHERE rowid=?",
                    (*params, row["rowid"]),
                )
        else:
            columns = ", ".join(f'"{k}"' for k in values)
            placeholders = ", ".join("?" for _ in values)
            await self.bot.db.execute(
                f"INSERT INTO channel_state ({columns}) VALUES ({placeholders})",
                tuple(values.values()),
            )
        await self.bot.db.commit()

    async def _record(self, message, direct):
        guild_id = message.guild.id if message.guild else None
        now = datetime.now(timezone.utc).isoformat()

        await self._record_message(message, guild_id, now, direct)
        await self._record_user(message, now)

        if guild_id:
            await self._record_relationship(message, guild_id, now)
            await self._record_channel(message, guild_id, now)

        await self.bot.db.commit()

    async def _record_message(self, message, guild_id, now, direct):
        cols = await table_columns(self.bot.db, "messages")
        values = {}

        aliases = {
            "discord_id": message.id,
            "discord_message_id": message.id,
            "guild_id": guild_id,
            "channel_id": message.channel.id,
            "author_id": message.author.id,
            "author_discord_id": message.author.id,
            "content": message.content,
            "created_at": now,
            "is_direct": int(direct),
        }
        for column, value in aliases.items():
            if column in cols:
                values[column] = value

        # Existing canonical schemas may have required columns not present in
        # v0.1. Supply the common equivalents when they exist.
        await self._insert_if_absent(
            "messages",
            values,
            unique_checks=(
                ("discord_id", message.id),
                ("discord_message_id", message.id),
            ),
        )

    async def _record_user(self, message, now):
        cols = await table_columns(self.bot.db, "users")
        user_id = message.author.id

        identity_column = (
            "discord_id" if "discord_id" in cols else
            "id" if "id" in cols else None
        )
        if identity_column is None:
            raise RuntimeError("users table has no usable identity column")

        row = None
        if "discord_id" in cols:
            row = await fetchone(
                self.bot.db,
                "SELECT rowid, * FROM users WHERE discord_id=? "
                "ORDER BY rowid DESC LIMIT 1",
                (user_id,),
            )
        if row is None and "id" in cols:
            row = await fetchone(
                self.bot.db,
                "SELECT rowid, * FROM users WHERE id=? "
                "ORDER BY rowid DESC LIMIT 1",
                (user_id,),
            )

        if row:
            assignments = {}
            for c, v in (
                ("discord_id", user_id),
                ("name", message.author.display_name),
                ("display_name", message.author.display_name),
                ("last_seen", now),
                ("last_seen_at", now),
            ):
                if c in cols and c != "id":
                    assignments[c] = v

            if "message_count" in cols:
                assignments["message_count"] = (row["message_count"] or 0) + 1

            if assignments:
                await self._update_row("users", row["rowid"], assignments)
            return

        values = {}
        if "id" in cols:
            values["id"] = user_id
        if "discord_id" in cols:
            values["discord_id"] = user_id
        if "name" in cols:
            values["name"] = message.author.display_name
        if "display_name" in cols:
            values["display_name"] = message.author.display_name
        if "first_seen" in cols:
            values["first_seen"] = now
        if "created_at" in cols:
            values["created_at"] = now
        if "last_seen" in cols:
            values["last_seen"] = now
        if "last_seen_at" in cols:
            values["last_seen_at"] = now
        if "message_count" in cols:
            values["message_count"] = 1

        await self._insert("users", values)

    async def _record_relationship(self, message, guild_id, now):
        cols = await table_columns(self.bot.db, "relationships")
        user_column = (
            "user_id" if "user_id" in cols else
            "user_discord_id" if "user_discord_id" in cols else None
        )
        if not user_column or "guild_id" not in cols:
            return

        row = await fetchone(
            self.bot.db,
            f'SELECT rowid, * FROM relationships '
            f'WHERE guild_id=? AND "{user_column}"=? '
            f'ORDER BY rowid DESC LIMIT 1',
            (guild_id, message.author.id),
        )

        if row:
            values = {}
            if "familiarity" in cols:
                values["familiarity"] = min(
                    1, float(row["familiarity"] or 0) + 0.01
                )
            if "last_interaction" in cols:
                values["last_interaction"] = now
            if "updated_at" in cols:
                values["updated_at"] = now
            await self._update_row("relationships", row["rowid"], values)
            return

        values = {"guild_id": guild_id, user_column: message.author.id}
        defaults = {
            "familiarity": 0.01,
            "trust": 0.5,
            "closeness": 0,
            "impression": "",
            "last_interaction": now,
            "updated_at": now,
        }
        for c, v in defaults.items():
            if c in cols:
                values[c] = v
        await self._insert("relationships", values)

    async def _record_channel(self, message, guild_id, now):
        cols = await table_columns(self.bot.db, "channel_state")
        if not {"guild_id", "channel_id"} <= cols:
            return

        row = await fetchone(
            self.bot.db,
            "SELECT rowid, * FROM channel_state "
            "WHERE guild_id=? AND channel_id=? "
            "ORDER BY rowid DESC LIMIT 1",
            (guild_id, message.channel.id),
        )
        if row:
            if "last_activity" in cols:
                await self._update_row(
                    "channel_state",
                    row["rowid"],
                    {"last_activity": now},
                )
            return

        values = {"guild_id": guild_id, "channel_id": message.channel.id}
        if "last_activity" in cols:
            values["last_activity"] = now
        await self._insert("channel_state", values)

    async def _insert_if_absent(self, table, values, unique_checks=()):
        for column, value in unique_checks:
            if column in values:
                row = await fetchone(
                    self.bot.db,
                    f'SELECT rowid FROM "{table}" WHERE "{column}"=? '
                    f'ORDER BY rowid DESC LIMIT 1',
                    (value,),
                )
                if row:
                    return
        await self._insert(table, values)

    async def _insert(self, table, values):
        if not values:
            raise RuntimeError(f"No compatible columns available for {table}")

        columns = ", ".join(f'"{k}"' for k in values)
        placeholders = ", ".join("?" for _ in values)
        await self.bot.db.execute(
            f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
            tuple(values.values()),
        )

    async def _update_row(self, table, rowid, values):
        if not values:
            return
        assignments = ", ".join(f'"{k}"=?' for k in values)
        await self.bot.db.execute(
            f'UPDATE "{table}" SET {assignments} WHERE rowid=?',
            (*values.values(), rowid),
        )

    async def _relationship(self, message):
        if not message.guild:
            return {}

        cols = await table_columns(self.bot.db, "relationships")
        user_column = (
            "user_id" if "user_id" in cols else
            "user_discord_id" if "user_discord_id" in cols else None
        )
        if not user_column:
            return {}

        wanted = [
            c for c in (
                "familiarity",
                "trust",
                "closeness",
                "impression",
                "last_interaction",
            )
            if c in cols
        ]
        if not wanted:
            return {}

        row = await fetchone(
            self.bot.db,
            f'SELECT {", ".join(wanted)} FROM relationships '
            f'WHERE guild_id=? AND "{user_column}"=? '
            f'ORDER BY rowid DESC LIMIT 1',
            (message.guild.id, message.author.id),
        )
        return dict(row) if row else {}

    def _apply_emotion(self, label):
        label = (label or "").lower()
        if "happy" in label or "joy" in label:
            self.emotion.mood = "happy"
            self.emotion.sociability = min(1, self.emotion.sociability + 0.06)
        elif "sad" in label:
            self.emotion.mood = "sad"
        elif "annoy" in label or "frustr" in label:
            self.emotion.mood = "annoyed"
        elif "curious" in label:
            self.emotion.mood = "curious"
            self.emotion.curiosity = min(1, self.emotion.curiosity + 0.08)
        elif label:
            self.emotion.mood = label[:40]
