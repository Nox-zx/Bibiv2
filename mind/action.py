from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_core.schemas import CognitiveDecision


@dataclass(frozen=True)
class ValidatedAction:
    type: str
    target: str | None
    parameters: dict[str, str]
    reason: str


class ActionController:
    """Validates cognitive actions before the Discord layer executes them."""

    ALLOWED_TYPES = {
        "reply",
        "react",
        "start_game",
        "suggest_game",
        "create_event",
        "change_channel",
    }

    def validate(self, decision: CognitiveDecision) -> list[ValidatedAction]:
        result: list[ValidatedAction] = []

        for action in decision.actions:
            if action.type not in self.ALLOWED_TYPES:
                continue

            parameters: dict[str, str] = {}
            for item in action.parameters:
                parameters[item.key] = item.value

            result.append(
                ValidatedAction(
                    type=action.type,
                    target=action.target,
                    parameters=parameters,
                    reason=action.reason,
                )
            )

        return result

    @staticmethod
    def response_text(decision: CognitiveDecision, max_length: int) -> str:
        if not decision.response:
            return ""
        return decision.response[:max_length]
