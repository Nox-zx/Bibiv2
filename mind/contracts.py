from dataclasses import dataclass, field
from typing import Any

@dataclass
class CognitiveContext:
    self_model: dict[str, Any]
    emotional_state: dict[str, Any]
    world: dict[str, Any]
    perception: dict[str, Any]
    attention: dict[str, Any]
    relationship: dict[str, Any]
    memories: list[dict[str, Any]] = field(default_factory=list)
    conversation: list[dict[str, Any]] = field(default_factory=list)
    temporal_context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return self.__dict__

@dataclass
class CognitiveDecision:
    should_respond: bool
    intention: str
    emotion: str
    internal_state_update: dict[str, Any]
    response: str
    memory_candidates: list[dict[str, Any]]
    relationship_update: dict[str, Any]
    initiative: bool = False
