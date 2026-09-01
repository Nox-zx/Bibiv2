from __future__ import annotations

import json
from typing import Any

from ai_core.gateway import GeminiGateway
from ai_core.prompts import COGNITIVE
from ai_core.schemas import CognitiveDecision


class CognitiveMind:
    """Cognitive boundary.

    The mind receives an assembled Bibi context instead of a raw Discord
    message. Discord facts are assembled outside Gemini; Gemini interprets
    the supplied world, memory, social and internal context.
    """

    def __init__(self, gateway: GeminiGateway, model: str, thinking_level: str):
        self.gateway = gateway
        self.model = model
        self.thinking_level = thinking_level

    async def decide(self, context: dict[str, Any]) -> CognitiveDecision:
        input_text = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )
        return await self.gateway.structured(
            model=self.model,
            system_instruction=COGNITIVE,
            input_text=input_text,
            response_schema=CognitiveDecision,
            thinking_level=self.thinking_level,
        )
