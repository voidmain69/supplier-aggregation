"""Per-principal token-bucket rate limiter (pure domain — no I/O, no framework).

Each key (principal subject) gets a bucket that refills at ``rate_per_second`` up to
``burst``. :meth:`allow` is non-blocking: it returns ``False`` when the bucket is empty so
the caller can answer 429 immediately rather than queueing. The clock is injectable so the
loop is deterministic in tests.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class RateLimiter:
    """A monotonic token-bucket limiter keyed by an arbitrary string (e.g. principal)."""

    def __init__(
        self,
        *,
        rate_per_second: float,
        burst: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._rate = rate_per_second
        self._burst = float(burst)
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_seen)

    def allow(self, key: str, *, cost: float = 1.0) -> bool:
        """Consume ``cost`` tokens for ``key``; return whether the request is allowed."""
        now = self._clock()
        tokens, last = self._buckets.get(key, (self._burst, now))
        tokens = min(self._burst, tokens + (now - last) * self._rate)
        if tokens >= cost:
            self._buckets[key] = (tokens - cost, now)
            return True
        self._buckets[key] = (tokens, now)
        return False

    def retry_after(self, key: str, *, cost: float = 1.0) -> int:
        """Seconds until ``cost`` tokens are available for ``key`` (for the Retry-After hint)."""
        if self._rate <= 0:
            return 1
        tokens, _ = self._buckets.get(key, (self._burst, self._clock()))
        missing = max(0.0, cost - tokens)
        return max(1, int(missing / self._rate + 0.999))
