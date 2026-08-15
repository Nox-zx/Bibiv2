from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    discord_token: str
    gemini_api_key: str
    guild_id: int | None
    creator_id: int | None
    cognitive_model: str
    reflective_model: str
    cognitive_thinking: str
    reflective_thinking: str
    database_url: str
    context_message_limit: int
    attention_minutes: int
    reflection_minutes: int
    max_response_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bibi.db")
        if database_url.startswith("sqlite"):
            Path("data").mkdir(parents=True, exist_ok=True)

        guild_raw = os.getenv("GUILD_ID")
        creator_raw = os.getenv("CREATOR_ID")
        return cls(
            discord_token=_required("DISCORD_TOKEN"),
            gemini_api_key=_required("GEMINI_API_KEY"),
            guild_id=int(guild_raw) if guild_raw else None,
            creator_id=int(creator_raw) if creator_raw else None,
            cognitive_model=os.getenv("COGNITIVE_MODEL", "gemini-3.6-flash"),
            reflective_model=os.getenv("REFLECTIVE_MODEL", "gemini-3.5-flash-lite"),
            cognitive_thinking=os.getenv("COGNITIVE_THINKING", "medium"),
            reflective_thinking=os.getenv("REFLECTIVE_THINKING", "low"),
            database_url=database_url,
            context_message_limit=int(os.getenv("CONTEXT_MESSAGE_LIMIT", "25")),
            attention_minutes=int(os.getenv("ATTENTION_MINUTES", "20")),
            reflection_minutes=int(os.getenv("REFLECTION_MINUTES", "360")),
            max_response_length=int(os.getenv("MAX_RESPONSE_LENGTH", "1200")),
        )
