from dataclasses import dataclass
from os import getenv
from dotenv import load_dotenv

load_dotenv()

def _int(name: str, default: int) -> int:
    try:
        return int(getenv(name, str(default)))
    except ValueError:
        return default

@dataclass(frozen=True)
class Settings:
    discord_token: str = getenv("DISCORD_TOKEN", "")
    cognitive_model: str = getenv("COGNITIVE_MODEL", "gemini-3.5-flash-lite")
    reflective_model: str = getenv("REFLECTIVE_MODEL", "gemini-3.5-flash-lite")
    database_path: str = getenv("DATABASE_PATH", "data/bibi.db")
    context_message_limit: int = _int("CONTEXT_MESSAGE_LIMIT", 20)
    max_response_length: int = _int("MAX_RESPONSE_LENGTH", 1200)
    attention_active_minutes: int = _int("ATTENTION_ACTIVE_MINUTES", 20)
    reflection_interval_minutes: int = _int("REFLECTION_INTERVAL_MINUTES", 360)
    log_level: str = getenv("LOG_LEVEL", "INFO")
    home_guild_id: int | None = _int("BIBI_HOME_GUILD_ID", 0) or None
    creator_id: int | None = _int("BIBI_CREATOR_ID", 0) or None

    @property
    def gemini_keys(self) -> list[str]:
        return [k for k in (
            getenv("GEMINI_API_KEY_1", ""),
            getenv("GEMINI_API_KEY_2", ""),
            getenv("GEMINI_API_KEY_3", ""),
            getenv("GEMINI_API_KEY_4", ""),
        ) if k]

settings = Settings()
