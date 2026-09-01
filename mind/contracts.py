from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AttentionDecision:
    should_consider: bool
    priority: int
    reason: str
    direct_address: bool = False


@dataclass(frozen=True)
class CognitiveContext:
    perception: dict[str, Any]
    world: dict[str, Any]
    attention: AttentionDecision
    time_context: dict[str, Any]
    relationship: dict[str, Any] | None
    self_model: dict[str, Any] | None
    memories: list[dict[str, Any]] = field(default_factory=list)
    internal_state: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "perception": self.perception,
            "world": self.world,
            "attention": {
                "should_consider": self.attention.should_consider,
                "priority": self.attention.priority,
                "reason": self.attention.reason,
                "direct_address": self.attention.direct_address,
            },
            "time_context": self.time_context,
            "relationship": self.relationship,
            "self_model": self.self_model,
            "memories": self.memories,
            "internal_state": self.internal_state,
        }


@dataclass(frozen=True)
class Experience:
    event_type: str
    timestamp: str
    guild_id: int | None
    channel_id: int | None
    actor_id: int | None
    summary: str
    outcome: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "actor_id": self.actor_id,
            "summary": self.summary,
            "outcome": self.outcome,
            "metadata": self.metadata,
        }
