from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

LUANDA_TZ = ZoneInfo("Africa/Luanda")


def get_time_context(now: datetime | None = None) -> dict[str, str]:
    """Return the authoritative current date/time for Bibi's cognitive context."""
    if now is None:
        now = datetime.now(LUANDA_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=LUANDA_TZ)
    else:
        now = now.astimezone(LUANDA_TZ)

    weekdays = (
        "segunda-feira",
        "terça-feira",
        "quarta-feira",
        "quinta-feira",
        "sexta-feira",
        "sábado",
        "domingo",
    )

    return {
        "timezone": "Africa/Luanda",
        "utc_offset": now.strftime("UTC%z"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": weekdays[now.weekday()],
        "iso": now.isoformat(),
    }