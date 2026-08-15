from __future__ import annotations

import discord
from discord import app_commands


async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("pong")


def register_commands(tree: app_commands.CommandTree) -> None:
    tree.add_command(app_commands.Command(name="ping", description="Testa se a Bibi está online.", callback=ping))
