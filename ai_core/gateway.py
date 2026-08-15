from __future__ import annotations

import asyncio
import copy
import json
import logging
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
LOGGER = logging.getLogger(__name__)


_UNSUPPORTED_SCHEMA_KEYS = {
    "$schema",
    "$defs",
    "$ref",
    "title",
    "description",
    "default",
    "examples",
    "additionalProperties",
}


def _gemini_schema(model: type[BaseModel]) -> dict[str, Any]:
    raw = copy.deepcopy(model.model_json_schema())
    definitions = raw.get("$defs", {})

    def resolve(value: Any) -> Any:
        if isinstance(value, list):
            return [resolve(item) for item in value]

        if not isinstance(value, dict):
            return value

        reference = value.get("$ref")
        if reference and reference.startswith("#/$defs/"):
            name = reference.split("/")[-1]
            return resolve(copy.deepcopy(definitions[name]))

        any_of = value.get("anyOf")
        if isinstance(any_of, list):
            non_null = [item for item in any_of if item != {"type": "null"}]
            if len(non_null) == 1:
                return resolve(non_null[0])
            return {"anyOf": [resolve(item) for item in any_of]}

        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in _UNSUPPORTED_SCHEMA_KEYS:
                continue
            result[key] = resolve(item)
        return result

    return resolve(raw)


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
        schema = _gemini_schema(response_schema)

        for attempt in range(retries + 1):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=model,
                    contents=input_text,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=schema,
                        thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
                    ),
                )
                if not response.text:
                    raise RuntimeError("Gemini returned an empty response")
                return response_schema.model_validate(json.loads(response.text))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                LOGGER.exception(
                    "Gemini structured call failed (attempt %s/%s)",
                    attempt + 1,
                    retries + 1,
                )
                if attempt < retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Gemini request failed") from last_error