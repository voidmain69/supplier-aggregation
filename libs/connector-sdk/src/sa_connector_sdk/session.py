"""Per-account session cache with single-flight re-authentication.

Brain (and similar) issue a session id (SID) from an auth call; subsequent requests reuse
it until it expires. This caches the token per account, re-authenticates on expiry or
explicit invalidation, and guarantees only one auth call happens at a time even under
concurrent access (single-flight) so we don't burn the rate budget on redundant logins.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

Authenticate = Callable[[], Awaitable[str]]
Monotonic = Callable[[], float]


class SessionManager:
    """Caches one session token, refreshing it when stale."""

    def __init__(
        self,
        authenticate: Authenticate,
        *,
        ttl_seconds: float,
        monotonic: Monotonic = time.monotonic,
    ) -> None:
        self._authenticate = authenticate
        self._ttl = ttl_seconds
        self._monotonic = monotonic
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    def _valid_token(self) -> str | None:
        if self._token is not None and self._monotonic() < self._expires_at:
            return self._token
        return None

    async def get(self) -> str:
        """Return a valid session token, authenticating if needed (single-flight)."""
        token = self._valid_token()
        if token is not None:
            return token
        async with self._lock:
            # Another waiter may have refreshed while we waited for the lock.
            token = self._valid_token()
            if token is not None:
                return token
            token = await self._authenticate()
            self._token = token
            self._expires_at = self._monotonic() + self._ttl
            return token

    async def invalidate(self) -> None:
        """Drop the cached token so the next ``get`` re-authenticates (e.g. after a 401)."""
        async with self._lock:
            self._token = None
            self._expires_at = 0.0
