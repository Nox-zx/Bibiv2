from __future__ import annotations

import asyncio
import json
import logging
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
LOGGER = logging.getLogger(__name__)


class GeminiGateway:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)

    async def structured(
        self,
        *,
        model: str,
        system_instruction: str,
        input_text: str,
        response_schema: type[T],
        thinking_level: str,
        retries: int = 2,
    ) -> T:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=input_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    ),
                )
                if not response.text:
                    raise RuntimeError("Gemini returned an empty response")
                return response_schema.model_validate(json.loads(response.text))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Gemini request failed") from last_error