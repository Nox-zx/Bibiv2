from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MemoryCandidate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    kind: Literal["factual", "episodic", "social", "relationship", "preference"]
    scope: Literal["public", "channel", "user_private", "bibi_internal"] = "public"
    importance: Literal["temporary", "normal", "important", "permanent"] = "normal"
    confidence: Literal["low", "medium", "high"] = "medium"
    owner_discord_id: int | None = None


class RelationshipUpdate(BaseModel):
    user_discord_id: int
    familiarity_delta: float = Field(default=0.0, ge=-1, le=1)
    trust_delta: float = Field(default=0.0, ge=-1, le=1)
    closeness_delta: float = Field(default=0.0, ge=-1, le=1)
    impression: str | None = Field(default=None, max_length=400)


class ActionParameter(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(default="", max_length=300)


class ActionProposal(BaseModel):
    type: Literal[
        "reply",
        "react",
        "start_game",
        "suggest_game",
        "create_event",
        "change_channel",
    ]
    target: str | None = None
    parameters: list[ActionParameter] = Field(default_factory=list, max_length=10)
    reason: str = Field(default="", max_length=300)


class CognitiveDecision(BaseModel):
    participation: Literal["respond", "silent", "ask_clarification", "react_only"]
    confidence: float = Field(ge=0, le=1)
    interpretation: str = Field(max_length=500)
    emotional_state: str = Field(max_length=100)
    social_read: str = Field(max_length=400)
    intention: str = Field(max_length=200)
    response: str = Field(default="", max_length=1200)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list, max_length=5)
    relationship_updates: list[RelationshipUpdate] = Field(default_factory=list, max_length=5)
    self_observations: list[str] = Field(default_factory=list, max_length=3)
    actions: list[ActionProposal] = Field(default_factory=list, max_length=3)
    reflection_trigger: bool = False


class SelfModelChange(BaseModel):
    area: Literal["trait", "preference", "value", "habit", "interest", "self_image"]
    change: str = Field(max_length=500)
    severity: Literal["minor", "moderate", "major"] = "minor"
    evidence_summary: str = Field(max_length=500)


class ReflectionResult(BaseModel):
    insights: list[str] = Field(default_factory=list, max_length=8)
    self_model_changes: list[SelfModelChange] = Field(default_factory=list, max_length=5)
    memory_updates: list[MemoryCandidate] = Field(default_factory=list, max_length=8)
    memories_to_forget: list[int] = Field(default_factory=list, max_length=10)
    relationship_updates: list[RelationshipUpdate] = Field(default_factory=list, max_length=8)
    new_curiosities: list[str] = Field(default_factory=list, max_length=5)
    diary_entries: list[str] = Field(default_factory=list, max_length=3)
    behaviour_adjustments: list[str] = Field(default_factory=list, max_length=5)