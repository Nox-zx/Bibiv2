from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class EmotionalState:
    mood: str = "neutral"
    energy: float = 0.7
    sociability: float = 0.6
    curiosity: float = 0.5
    last_update: str = ""

    def as_dict(self):
        return {
            "mood": self.mood,
            "energy": round(self.energy, 2),
            "sociability": round(self.sociability, 2),
            "curiosity": round(self.curiosity, 2),
            "last_update": self.last_update,
        }

def time_adjustment(hour: int) -> dict:
    if 5 <= hour < 10:
        return {"energy": -0.15, "sociability": -0.10, "tone": "quiet_morning"}
    if 10 <= hour < 17:
        return {"energy": 0.05, "sociability": 0.05, "tone": "day"}
    if 17 <= hour < 23:
        return {"energy": 0.10, "sociability": 0.10, "tone": "evening"}
    return {"energy": -0.10, "sociability": -0.05, "tone": "late_night"}

def update_emotion(state: EmotionalState, event: str):
    adj = {
        "positive": (0.08, 0.06, 0.05),
        "negative": (-0.08, -0.05, 0.02),
        "interesting": (0.04, 0.03, 0.12),
        "boring": (-0.03, -0.02, -0.06),
    }.get(event, (0,0,0))
    state.energy=max(0,min(1,state.energy+adj[0]))
    state.sociability=max(0,min(1,state.sociability+adj[1]))
    state.curiosity=max(0,min(1,state.curiosity+adj[2]))
    state.last_update=datetime.now(timezone.utc).isoformat()
