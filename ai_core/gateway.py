import asyncio
import time
import logging
from dataclasses import dataclass
from google import genai
from google.genai import types

log=logging.getLogger(__name__)

@dataclass
class KeyState:
    key: str
    cooldown_until: float=0.0
    failures: int=0
    last_used: float=0.0

class GeminiGateway:
    def __init__(self, keys: list[str]):
        if not keys:
            raise RuntimeError("No Gemini API keys configured.")
        self.keys=[KeyState(k) for k in keys[:4]]
        self.lock=asyncio.Lock()

    async def _pick(self):
        async with self.lock:
            now=time.monotonic()
            available=[k for k in self.keys if k.cooldown_until <= now]
            if not available:
                return min(self.keys, key=lambda x:x.cooldown_until)
            return min(available, key=lambda x:x.last_used)

    async def generate(self, *, model, system, payload, schema):
        last_error=None
        for _ in range(len(self.keys)):
            state=await self._pick()
            now=time.monotonic()
            if state.cooldown_until>now:
                await asyncio.sleep(min(state.cooldown_until-now, 3))
            try:
                client=genai.Client(api_key=state.key)
                state.last_used=time.monotonic()
                result=await asyncio.to_thread(
                    client.models.generate_content,
                    model=model,
                    contents=payload,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.8,
                    ),
                )
                state.failures=0
                return result.parsed
            except Exception as exc:
                last_error=exc
                state.failures+=1
                state.cooldown_until=time.monotonic()+min(30*(2**(state.failures-1)),300)
                log.warning("Gemini key failed; rotating. failures=%s",state.failures)
        raise RuntimeError(f"All Gemini keys failed: {last_error}")
