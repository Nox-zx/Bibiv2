from __future__ import annotations

import logging

import discord
from discord import app_commands

from ai_core.cognitive import CognitiveMind
from ai_core.gateway import GeminiGateway
from bot.commands import register_commands
from config.settings import Settings
from database.engine import create_engine, create_session_factory, init_db
from bot.events import handle_message

LOGGER = logging.getLogger(__name__)


class BibiClient(discord.Client):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(intents=intents)

        self.settings = settings
        self.tree = app_commands.CommandTree(self)
        self.db_engine = create_engine(settings.database_url)
        self.session_factory = create_session_factory(self.db_engine)
        gateway = GeminiGateway(settings.gemini_api_key)
        self.cognitive_mind = CognitiveMind(
            gateway,
            settings.cognitive_model,
            settings.cognitive_thinking,
        )

    async def setup_hook(self) -> None:
        await init_db(self.db_engine)

        # Remove stale global commands left by older versions of the bot.
        self.tree.clear_commands(guild=None)
        await self.tree.sync()

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.clear_commands(guild=guild)
            register_commands(self.tree, guild=guild)
            await self.tree.sync(guild=guild)
        else:
            register_commands(self.tree)
            await self.tree.sync()

        LOGGER.info("Bibi setup complete")

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "?")

    async def on_message(self, message: discord.Message) -> None:
        if not self.user:
            return
        await handle_message(
            message,
            bot_user_id=self.user.id,
            session_factory=self.session_factory,
            cognitive_mind=self.cognitive_mind,
            attention_minutes=self.settings.attention_minutes,
            max_response_length=self.settings.max_response_length,
        )