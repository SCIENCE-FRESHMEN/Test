from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TypeVar

from .settings import Settings

T = TypeVar("T")


class ApiRateLimiter:
    """Small async limiter for model-backed extensions.

    The deterministic demo does not need remote calls, but DeepSeek/OpenAI-compatible
    Agent runs can reuse this limiter to avoid 429 bursts.
    """

    def __init__(self, settings: Settings) -> None:
        self.interval = settings.api_request_interval_seconds
        self.retry_attempts = settings.api_retry_attempts
        self.retry_backoff = settings.api_retry_backoff_seconds
        self._semaphore = asyncio.Semaphore(settings.api_max_concurrency)
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def run(self, call: Callable[[], Awaitable[T]]) -> T:
        async with self._semaphore:
            last_error: Exception | None = None
            for attempt in range(1, self.retry_attempts + 1):
                await self._wait_turn()
                try:
                    return await call()
                except Exception as exc:  # noqa: BLE001 - caller may use SDK-specific errors.
                    last_error = exc
                    if attempt >= self.retry_attempts or not _looks_retryable(exc):
                        raise
                    await asyncio.sleep(self.retry_backoff * attempt)
            if last_error:
                raise last_error
            raise RuntimeError("API call failed without an exception")

    async def _wait_turn(self) -> None:
        async with self._lock:
            elapsed = monotonic() - self._last_request
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
            self._last_request = monotonic()


def _looks_retryable(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(token in text for token in ["429", "rate limit", "timeout", "temporarily", "503", "502"])
