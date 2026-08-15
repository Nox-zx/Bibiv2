from __future__ import annotations

import logging

from bot.client import BibiClient
from config.settings import Settings
from utils.logging import configure_logging


def main() -> None:
    configure_logging()
    settings = Settings.from_env()
    client = BibiClient(settings)
    from bot.commands import register_commands
    register_commands(client.tree)
    client.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
