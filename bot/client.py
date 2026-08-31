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
from world.events import sync_channel_event, sync_guild_event, sync_member_event, sync_role_event
from world.sync import sync_guild_world

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
        gateway = GeminiGateway(api_keys=list(settings.gemini_api_keys))
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
        guilds = []
        if self.settings.guild_id is not None:
            guild = self.get_guild(self.settings.guild_id)
            if guild is not None:
                guilds = [guild]
            else:
                LOGGER.warning("Configured GUILD_ID %s is not currently available in cache", self.settings.guild_id)
        else:
            guilds = list(self.guilds)

        for guild in guilds:
            try:
                await sync_guild_world(
                    guild,
                    session_factory=self.session_factory,
                    fetch_members=True,
                )
            except Exception:
                LOGGER.exception("Initial World Model sync failed for guild %s", guild.id)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        await sync_guild_event(after, session_factory=self.session_factory)

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        await sync_channel_event(channel, session_factory=self.session_factory, active=True)

    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ) -> None:
        await sync_channel_event(after, session_factory=self.session_factory, active=True)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await sync_channel_event(channel, session_factory=self.session_factory, active=False)

    async def on_guild_role_create(self, role: discord.Role) -> None:
        await sync_role_event(role, session_factory=self.session_factory, active=True)

    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        await sync_role_event(after, session_factory=self.session_factory, active=True)

    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await sync_role_event(role, session_factory=self.session_factory, active=False)

    async def on_member_join(self, member: discord.Member) -> None:
        await sync_member_event(member, session_factory=self.session_factory, active=True)

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        await sync_member_event(after, session_factory=self.session_factory, active=True)

    async def on_member_remove(self, member: discord.Member) -> None:
        await sync_member_event(member, session_factory=self.session_factory, active=False)

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