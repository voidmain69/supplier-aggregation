"""Helpers for testing connectors deterministically.

- :class:`FakeClock` drives the rate limiter and session manager without real waits — its
  ``sleep`` advances virtual time, so a "3 req/s" test asserts exact timings instantly.
- :func:`implements_connector` checks a class satisfies the SupplierConnector protocol.
- :func:`collect` drains an async iterator into a list.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sa_connector_sdk.protocol import SupplierConnector


class FakeClock:
    """A virtual monotonic clock whose ``sleep`` fast-forwards time."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def monotonic(self) -> float:
        return self._now

    async def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._now += seconds

    def advance(self, seconds: float) -> None:
        self._now += seconds


def implements_connector(candidate: Any) -> bool:
    """Return True if the object satisfies the SupplierConnector protocol."""
    return isinstance(candidate, SupplierConnector)


async def collect[T](iterator: AsyncIterator[T]) -> list[T]:
    """Drain an async iterator into a list."""
    return [item async for item in iterator]
