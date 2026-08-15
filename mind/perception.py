from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Perception:
    message_id: int
    guild_id: int | None
    channel_id: int
    author_id: int
    author_name: str
    content: str
    timestamp: datetime
    is_reply: bool
    mentioned_bibi: bool
    replied_message_content: str | None
    recent_messages: list[dict]

    def as_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "is_reply": self.is_reply,
            "mentioned_bibi": self.mentioned_bibi,
            "replied_message_content": self.replied_message_content,
            "recent_messages": self.recent_messages,
        }
