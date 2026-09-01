import logging
import discord
from discord.ext import tasks
from database.db import connect
from ai_core.gateway import GeminiGateway
from ai_core.cognitive import CognitiveMind
from ai_core.reflective import ReflectiveMind
from config.settings import settings
from .events import MessageProcessor

log=logging.getLogger(__name__)

class BibiClient(discord.Client):
    def __init__(self):
        intents=discord.Intents.default()
        intents.message_content=True
        intents.members=True
        super().__init__(intents=intents)
        self.db=None
        self.gateway=GeminiGateway(settings.gemini_keys)
        self.cognitive=CognitiveMind(self.gateway, settings.cognitive_model)
        self.reflective=ReflectiveMind(self.gateway, settings.reflective_model)
        self.processor=None
        self.reflection_loop.start()

    async def setup_hook(self):
        self.db=await connect(settings.database_path)
        self.processor=MessageProcessor(self)

    async def on_ready(self):
        log.info("Bibi online as %s | home=%s", self.user, settings.home_guild_id)

    async def on_message(self, message: discord.Message):
        if self.user and message.author.id==self.user.id:
            return
        if self.processor:
            await self.processor.process(message)

    @tasks.loop(minutes=60)
    async def reflection_loop(self):
        if self.db is None:
            return
        # v0.1 keeps reflection conservative: only selected summaries later.
        # The second Gemini role is available but not run on every message.

    @reflection_loop.before_loop
    async def before_reflection(self):
        await self.wait_until_ready()

    async def close(self):
        self.reflection_loop.cancel()
        if self.db:
            await self.db.close()
        await super().close()
