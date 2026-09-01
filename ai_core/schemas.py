from pydantic import BaseModel, Field

class MemoryCandidate(BaseModel):
    kind: str = "episodic"
    content: str
    importance: float = Field(default=0.5, ge=0, le=1)
    user_id: int | None = None

class CognitiveOutput(BaseModel):
    should_respond: bool
    intention: str
    emotion: str
    internal_state_update: dict = Field(default_factory=dict)
    response: str = ""
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list)
    relationship_update: dict = Field(default_factory=dict)
    initiative: bool = False

class ReflectionOutput(BaseModel):
    insights: list[str] = Field(default_factory=list)
    memory_updates: list[MemoryCandidate] = Field(default_factory=list)
    relationship_updates: list[dict] = Field(default_factory=list)
    self_updates: dict = Field(default_factory=dict)
