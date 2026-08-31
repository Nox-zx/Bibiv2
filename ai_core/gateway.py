from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
LOGGER = logging.getLogger(__name__)


class GeminiQuotaExceeded(RuntimeError):
    """Raised when all usable Gemini providers are quota-blocked."""


class GeminiTemporarilyUnavailable(RuntimeError):
    """Raised when Gemini providers cannot currently serve a request."""


class GeminiRequestError(RuntimeError):
    """Raised when the request itself is invalid and retrying another key is not useful."""


_UNSUPPORTED_SCHEMA_KEYS = {
    "$schema", "$defs", "$ref", "title", "description", "default", "examples",
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
            if name not in definitions:
                raise ValueError(f"Unknown schema definition: {name}")
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


def _error_text(exc: Exception) -> str:
    return str(exc).lower()


def _is_quota_error(exc: Exception) -> bool:
    text = _error_text(exc)
    return "429" in text or "resource_exhausted" in text or "quota exceeded" in text


def _is_auth_error(exc: Exception) -> bool:
    text = _error_text(exc)
    return "401" in text or "403" in text or "unauthenticated" in text or "permission denied" in text


def _is_client_request_error(exc: Exception) -> bool:
    text = _error_text(exc)
    return "400" in text or "invalid argument" in text or "bad request" in text


def _is_transient_error(exc: Exception) -> bool:
    text = _error_text(exc)
    return any(token in text for token in ("500", "502", "503", "504", "internal", "unavailable", "deadline exceeded", "timeout"))


def _next_pacific_midnight() -> datetime:
    pacific = ZoneInfo("America/Los_Angeles")
    now_local = datetime.now(pacific)
    next_day = (now_local + timedelta(days=1)).date()
    return datetime(next_day.year, next_day.month, next_day.day, tzinfo=pacific).astimezone(timezone.utc)


@dataclass
class _ProviderState:
    name: str
    api_key: str
    client: Any
    cooldown_until: float = 0.0
    invalid: bool = False
    consecutive_failures: int = 0
    last_used: float = 0.0

    @property
    def available(self) -> bool:
        return not self.invalid and time.monotonic() >= self.cooldown_until


class GeminiProviderPool:
    """Routes Gemini requests across independent API keys without exposing provider details upstream."""

    def __init__(self, api_keys: list[str], *, cooldown_seconds: float = 20.0):
        cleaned = []
        seen = set()
        for key in api_keys:
            key = key.strip()
            if key and key not in seen:
                cleaned.append(key)
                seen.add(key)
        if not cleaned:
            raise RuntimeError("No Gemini API keys configured")

        self._providers = [
            _ProviderState(f"provider-{index}", key, genai.Client(api_key=key))
            for index, key in enumerate(cleaned, start=1)
        ]
        self._cooldown_seconds = max(1.0, cooldown_seconds)
        self._selection_lock = asyncio.Lock()
        self._request_slots = asyncio.Semaphore(len(self._providers))

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    def _select_provider(self) -> _ProviderState | None:
        available = [provider for provider in self._providers if provider.available]
        if not available:
            return None
        # Least recently used first gives a simple, deterministic load spread.
        return min(available, key=lambda provider: provider.last_used)

    def _next_recovery(self) -> float | None:
        candidates = [p.cooldown_until for p in self._providers if not p.invalid and p.cooldown_until > time.monotonic()]
        return min(candidates) if candidates else None

    def _block(self, provider: _ProviderState, *, daily: bool) -> None:
        if daily:
            provider.cooldown_until = float("inf")
        else:
            provider.cooldown_until = time.monotonic() + self._cooldown_seconds
        provider.consecutive_failures += 1

    async def _pick(self) -> _ProviderState | None:
        async with self._selection_lock:
            provider = self._select_provider()
            if provider:
                provider.last_used = time.monotonic()
            return provider

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
        schema = _gemini_schema(response_schema)
        attempts_remaining = max(0, retries)
        tried: set[str] = set()
        last_error: Exception | None = None

        # A single logical request can fail over between providers. It never
        # blindly retries the same failed provider after a provider-level error.
        while True:
            provider = await self._pick()
            if provider is None:
                recovery = self._next_recovery()
                if recovery is not None and attempts_remaining > 0:
                    delay = max(0.0, recovery - time.monotonic())
                    await asyncio.sleep(min(delay, 5.0))
                    attempts_remaining -= 1
                    continue
                if all(p.invalid or p.cooldown_until == float("inf") for p in self._providers):
                    raise GeminiQuotaExceeded("All Gemini providers are quota-blocked") from last_error
                raise GeminiTemporarilyUnavailable("No Gemini provider is currently available") from last_error

            if provider.name in tried:
                provider.cooldown_until = time.monotonic() + self._cooldown_seconds
                continue
            tried.add(provider.name)

            try:
                async with self._request_slots:
                    response = await asyncio.to_thread(
                        provider.client.models.generate_content,
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
                result = response_schema.model_validate(json.loads(response.text))
                provider.consecutive_failures = 0
                provider.cooldown_until = 0.0
                LOGGER.debug("Gemini request served by %s", provider.name)
                return result

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if _is_client_request_error(exc):
                    LOGGER.error("Gemini rejected the request; not failing over: %s", exc)
                    raise GeminiRequestError("Gemini rejected the request") from exc

                if _is_auth_error(exc):
                    provider.invalid = True
                    provider.consecutive_failures += 1
                    LOGGER.error("%s disabled because its credentials/permissions were rejected", provider.name)
                elif _is_quota_error(exc):
                    daily = "perday" in _error_text(exc) or "per_day" in _error_text(exc) or "requests per day" in _error_text(exc) or "daily" in _error_text(exc)
                    self._block(provider, daily=daily)
                    LOGGER.warning("%s temporarily blocked after quota error (daily=%s)", provider.name, daily)
                elif _is_transient_error(exc):
                    self._block(provider, daily=False)
                    LOGGER.warning("%s temporarily blocked after transient Gemini error", provider.name)
                else:
                    self._block(provider, daily=False)
                    LOGGER.exception("%s failed with an unexpected Gemini error", provider.name)

                # Provider-level failure: move to another key. A retry budget is
                # used only for waiting/recovery, not for repeatedly hitting the same provider.
                if len(tried) >= len(self._providers):
                    if attempts_remaining > 0:
                        attempts_remaining -= 1
                        tried.clear()
                        await asyncio.sleep(min(1.5 * (retries - attempts_remaining + 1), 5.0))
                        continue
                    break

        if isinstance(last_error, GeminiRequestError):
            raise last_error
        raise GeminiTemporarilyUnavailable("Gemini request failed on all available providers") from last_error


class GeminiGateway:
    """Compatibility facade used by CognitiveMind and ReflectiveMind."""

    def __init__(self, api_key: str | None = None, *, api_keys: list[str] | None = None):
        keys = api_keys if api_keys is not None else ([api_key] if api_key else [])
        self.pool = GeminiProviderPool(keys)

    @property
    def provider_count(self) -> int:
        return self.pool.provider_count

    async def structured(self, **kwargs: Any) -> T:
        return await self.pool.structured(**kwargs)
