from __future__ import annotations

from datetime import datetime, timezone

from .contracts import Experience


def message_experience(
    *,
    guild_id: int | None,
    channel_id: int,
    actor_id: int,
    content: str,
    outcome: str | None = None,
) -> Experience:
    return Experience(
        event_type="message",
        timestamp=datetime.now(timezone.utc).isoformat(),
        guild_id=guild_id,
        channel_id=channel_id,
        actor_id=actor_id,
        summary=content[:500],
        outcome=outcome,
    )
