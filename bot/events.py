from datetime import datetime, timezone, timedelta
import discord
from mind.perception import Perception
from mind.attention import Attention
from mind.world import build_world
from mind.self_model import SELF_MODEL
from mind.contracts import CognitiveContext
from mind.emotion import EmotionalState, time_adjustment
from memory.store import retrieve, remember
from database.db import fetchone

class MessageProcessor:
    def __init__(self, bot):
        self.bot=bot
        self.attention=Attention()
        self.emotion=EmotionalState()

    async def process(self, message: discord.Message):
        recent=[]
        async for m in message.channel.history(limit=20, before=message):
            recent.append({
                "author": m.author.display_name,
                "author_id": m.author.id,
                "content": m.content,
                "time": m.created_at.isoformat(),
            })
        recent.reverse()

        direct=self._direct(message)
        reply=self._reply_to_bibi(message)
        state=await self._channel_engagement(message)

        attention=self.attention.decide(
            direct=direct,
            reply=reply,
            engaged=state,
            ambient_relevance=False,
        )
        if not attention.attend:
            await self._record(message, direct)
            return

        world=build_world(message.guild, message.channel, recent)
        temporal=time_adjustment(world["hour"])
        self.emotion.energy=max(0,min(1,self.emotion.energy+temporal["energy"]))
        self.emotion.sociability=max(0,min(1,self.emotion.sociability+temporal["sociability"]))

        relationship=await self._relationship(message)
        terms=message.content.replace("?"," ").split()[:12]
        memories=await retrieve(
            self.bot.db, terms,
            guild_id=message.guild.id if message.guild else None,
            user_id=message.author.id,
        )

        context=CognitiveContext(
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
            decision=await self.bot.cognitive.decide(context.as_dict())
        except Exception:
            # Do not expose API internals to users.
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
            text=decision.response.strip()[:1200]
            if text:
                await message.reply(text, mention_author=False)
                await self._set_channel_attention(message)

    def _direct(self,message):
        if self.bot.user and self.bot.user.mentioned_in(message):
            return True
        lowered=message.content.lower().strip()
        return any(lowered.startswith(x) for x in ("bibi ", "bibi,", "bibi:"))

    def _reply_to_bibi(self,message):
        ref=message.reference
        return bool(ref and ref.resolved and getattr(ref.resolved, "author", None) == self.bot.user)

    async def _channel_engagement(self, message):
        if not message.guild:
            return False
        row=await fetchone(
            self.bot.db,
            "SELECT attention_until FROM channel_state WHERE guild_id=? AND channel_id=?",
            (message.guild.id, message.channel.id),
        )
        if not row or not row["attention_until"]:
            return False
        try:
            return datetime.fromisoformat(row["attention_until"]) > datetime.now(timezone.utc)
        except ValueError:
            return False

    async def _set_channel_attention(self, message):
        if not message.guild:
            return
        now=datetime.now(timezone.utc)
        until=(now+timedelta(minutes=20)).isoformat()
        await self.bot.db.execute(
            """INSERT INTO channel_state
               (guild_id,channel_id,attention_until,last_bibi_message)
               VALUES(?,?,?,?)
               ON CONFLICT(guild_id,channel_id)
               DO UPDATE SET
                 attention_until=excluded.attention_until,
                 last_bibi_message=excluded.last_bibi_message""",
            (message.guild.id, message.channel.id, until, now.isoformat()),
        )
        await self.bot.db.commit()

    async def _record(self,message,direct):
        guild_id=message.guild.id if message.guild else None
        now=datetime.now(timezone.utc).isoformat()
        await self.bot.db.execute(
            """INSERT OR IGNORE INTO messages(discord_id,guild_id,channel_id,author_id,content,created_at,is_direct)
               VALUES(?,?,?,?,?,?,?)""",
            (message.id,guild_id,message.channel.id,message.author.id,message.content,now,int(direct)),
        )
        await self.bot.db.execute(
            """INSERT INTO users(id,name,first_seen,last_seen,message_count)
               VALUES(?,?,?,?,1)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name,last_seen=excluded.last_seen,message_count=users.message_count+1""",
            (message.author.id,message.author.display_name,now,now),
        )
        if guild_id:
            await self.bot.db.execute(
                """INSERT INTO relationships(guild_id,user_id,familiarity,trust,closeness,last_interaction)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(guild_id,user_id) DO UPDATE SET familiarity=MIN(1,familiarity+0.01),last_interaction=excluded.last_interaction""",
                (guild_id,message.author.id,0.01,0.5,0,now),
            )
            await self.bot.db.execute(
                """INSERT INTO channel_state(guild_id,channel_id,last_activity)
                   VALUES(?,?,?)
                   ON CONFLICT(guild_id,channel_id) DO UPDATE SET last_activity=excluded.last_activity""",
                (guild_id,message.channel.id,now),
            )
        await self.bot.db.commit()

    async def _relationship(self,message):
        if not message.guild:
            return {}
        row=await fetchone(self.bot.db, 
            "SELECT familiarity,trust,closeness,impression,last_interaction FROM relationships WHERE guild_id=? AND user_id=?",
            (message.guild.id,message.author.id),
        )
        return dict(row) if row else {}

    def _apply_emotion(self,label):
        label=(label or "").lower()
        if "happy" in label or "joy" in label:
            self.emotion.mood="happy"
            self.emotion.sociability=min(1,self.emotion.sociability+0.06)
        elif "sad" in label:
            self.emotion.mood="sad"
        elif "annoy" in label or "frustr" in label:
            self.emotion.mood="annoyed"
        elif "curious" in label:
            self.emotion.mood="curious"
            self.emotion.curiosity=min(1,self.emotion.curiosity+0.08)
        elif label:
            self.emotion.mood=label[:40]
