from __future__ import annotations

from ai_core.schemas import CognitiveDecision


class SafetyGuard:
    def validate_cognitive(self, decision: CognitiveDecision) -> CognitiveDecision:
        cleaned = decision.response.strip()
        decision.response = cleaned
        if len(cleaned) > 1200:
            decision.response = cleaned[:1197] + "..."
        if decision.participation == "silent":
            decision.response = ""
        return decision

    @staticmethod
    def is_private_action(action_type: str) -> bool:
        return action_type in {"admin_action", "expose_memory"}
