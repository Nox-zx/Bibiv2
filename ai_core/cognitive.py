import json
from .gateway import GeminiGateway
from .prompts import COGNITIVE_SYSTEM
from .schemas import CognitiveOutput

class CognitiveMind:
    def __init__(self, gateway: GeminiGateway, model: str):
        self.gateway=gateway
        self.model=model

    async def decide(self, context: dict) -> CognitiveOutput:
        return await self.gateway.generate(
            model=self.model,
            system=COGNITIVE_SYSTEM,
            payload=json.dumps(context, ensure_ascii=False, default=str),
            schema=CognitiveOutput,
        )
