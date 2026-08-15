from __future__ import annotations

import asyncio
import copy
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
LOGGER = logging.getLogger(__name__)


class GeminiQuotaExceeded(RuntimeError):
    """Raised when the Gemini project/model daily quota is exhausted."""


class GeminiTemporarilyUnavailable(RuntimeError):
    """Raised when Gemini cannot currently serve a request."""


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


def _is_daily_quota_error(exc: Exception) -> bool:
    text = str(exc)
    return (
        "429" in text
        and "RESOURCE_EXHAUSTED" in text
        and (
            "GenerateRequestsPerDayPerProject-FreeTier" in text
            or "requests per day" in text.lower()
            or "quota exceeded for metric" in text.lower()
        )
    )


def _next_pacific_midnight() -> datetime:
    """Return the next midnight in US Pacific time as an aware UTC datetime."""
    pacific = ZoneInfo("America/Los_Angeles")
    now_local = datetime.now(pacific)
    next_day = (now_local + timedelta(days=1)).date()
    next_midnight_local = datetime(
        next_day.year,
        next_day.month,
        next_day.day,
        tzinfo=pacific,
    )
    return next_midnight_local.astimezone(timezone.utc)


class GeminiGateway:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self._daily_quota_blocked_until: datetime | None = None
        self._request_lock = asyncio.Lock()

    @property
    def daily_quota_blocked(self) -> bool:
        if self._daily_quota_blocked_until is None:
            return False
        if datetime.now(timezone.utc) >= self._daily_quota_blocked_until:
            self._daily_quota_blocked_until = None
            return False
        return True

    @property
    def daily_quota_blocked_until(self) -> datetime | None:
        return self._daily_quota_blocked_until

    async def structured(
        self,
        *,
        model: str,
        system_instruction: str,
        input_text: str,
        response_schema: type[T],
        thinking_level: str,
        retries: int = 1,
    ) -> T:
        if self.daily_quota_blocked:
            raise GeminiQuotaExceeded(
                "Gemini daily quota is exhausted until "
                f"{self._daily_quota_blocked_until.isoformat()}"
            )

        last_error: Exception | None = None
        schema = _gemini_schema(response_schema)

        # Serialise outbound Gemini calls. This keeps bursts from the Discord
        # event loop from turning into a burst of API requests.
        async with self._request_lock:
            if self.daily_quota_blocked:
                raise GeminiQuotaExceeded(
                    "Gemini daily quota is exhausted until "
                    f"{self._daily_quota_blocked_until.isoformat()}"
                )

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

                    if _is_daily_quota_error(exc):
                        self._daily_quota_blocked_until = _next_pacific_midnight()
                        LOGGER.error(
                            "Gemini daily quota exhausted for model %s. "
                            "Disabling Gemini calls until %s.",
                            model,
                            self._daily_quota_blocked_until.isoformat(),
                        )
                        raise GeminiQuotaExceeded(
                            "Gemini daily quota exhausted"
                        ) from exc

                    LOGGER.exception(
                        "Gemini structured call failed (attempt %s/%s)",
                        attempt + 1,
                        retries + 1,
                    )
                    if attempt < retries:
                        await asyncio.sleep(1.5 * (attempt + 1))

        raise GeminiTemporarilyUnavailable("Gemini request failed") from last_error