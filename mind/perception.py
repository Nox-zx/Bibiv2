from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass
class Perception:
    message_id: int
    guild_id: int | None
    channel_id: int
    author_id: int
    author_name: str
    content: str
    created_at: datetime
    direct_address: bool
    reply_to_bibi: bool
    recent_messages: list[dict[str, Any]]

    def as_dict(self):
        return {
            "message_id": self.message_id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "author_id": self.author_id,
            "author_name": self.author_name,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "direct_address": self.direct_address,
            "reply_to_bibi": self.reply_to_bibi,
            "recent_messages": self.recent_messages,
        }
