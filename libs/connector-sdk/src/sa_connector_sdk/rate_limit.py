"""Async token-bucket rate limiter.

Suppliers cap request rates (Brain: 3 req/s per account). Every outbound call goes through
one of these so a connector can never exceed the budget. Time and sleep are injectable so
the limiter is deterministically testable without wall-clock waits (see test kit).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

Monotonic = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]

# Tolerance for float rounding so e.g. (1/3)*3 == 0.999...9 still satisfies "1 token".
_EPS = 1e-9


class AsyncTokenBucket:
    """A refilling token bucket. ``acquire`` blocks until a token is available."""

    def __init__(
        self,
        *,
        rate: float,
        capacity: float | None = None,
        monotonic: Monotonic = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._rate = rate
        self._capacity = capacity if capacity is not None else rate
        self._tokens = self._capacity
        self._monotonic = monotonic
        self._sleep = sleep
        self._last = monotonic()
        self._lock = asyncio.Lock()

    @property
    def tokens(self) -> float:
        """Best-effort current token count (without refilling); for tests/metrics."""
        return self._tokens

    def _refill(self) -> None:
        now = self._monotonic()
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last = now

    async def acquire(self, tokens: float = 1.0) -> None:
        """Consume ``tokens``, sleeping just long enough if the bucket is short."""
        if tokens > self._capacity:
            raise ValueError("cannot acquire more tokens than the bucket capacity")
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens - _EPS:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                await self._sleep(deficit / self._rate)
