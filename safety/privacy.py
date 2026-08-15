from __future__ import annotations


def can_expose_memory(*, scope: str, owner_discord_id: int | None, viewer_discord_id: int) -> bool:
    if scope in {"public", "channel"}:
        return True
    if scope == "user_private":
        return owner_discord_id == viewer_discord_id
    return False
