import json
from .gateway import GeminiGateway
from .prompts import REFLECTIVE_SYSTEM
from .schemas import ReflectionOutput

class ReflectiveMind:
    def __init__(self, gateway: GeminiGateway, model: str):
        self.gateway=gateway
        self.model=model

    async def reflect(self, context: dict) -> ReflectionOutput:
        return await self.gateway.generate(
            model=self.model,
            system=REFLECTIVE_SYSTEM,
            payload=json.dumps(context, ensure_ascii=False, default=str),
            schema=ReflectionOutput,
        )
