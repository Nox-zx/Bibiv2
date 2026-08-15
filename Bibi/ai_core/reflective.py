from __future__ import annotations

import json

from ai_core.gateway import GeminiGateway
from ai_core.prompts import REFLECTIVE
from ai_core.schemas import ReflectionResult


class ReflectiveMind:
    def __init__(self, gateway: GeminiGateway, model: str, thinking_level: str):
        self.gateway = gateway
        self.model = model
        self.thinking_level = thinking_level

    async def reflect(self, context: dict) -> ReflectionResult:
        input_text = json.dumps(context, ensure_ascii=False, default=str)
        return await self.gateway.structured(
            model=self.model,
            system_instruction=REFLECTIVE,
            input_text=input_text,
            response_schema=ReflectionResult,
            thinking_level=self.thinking_level,
        )
