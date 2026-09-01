import asyncio
import logging
from bot.client import BibiClient
from config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

async def main():
    bot = BibiClient()
    await bot.start(settings.discord_token)

if __name__ == "__main__":
    asyncio.run(main())
