from __future__ import annotations

import asyncio

from sa_connector_sdk.session import SessionManager
from sa_connector_sdk.testkit import FakeClock


class _Auth:
    """Counts auth calls and hands out incrementing tokens."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> str:
        self.calls += 1
        return f"SID-{self.calls}"


async def test_get__caches_within_ttl() -> None:
    auth = _Auth()
    clock = FakeClock()
    mgr = SessionManager(auth, ttl_seconds=10, monotonic=clock.monotonic)

    assert await mgr.get() == "SID-1"
    assert await mgr.get() == "SID-1"
    assert auth.calls == 1


async def test_get__reauth_after_ttl() -> None:
    auth = _Auth()
    clock = FakeClock()
    mgr = SessionManager(auth, ttl_seconds=10, monotonic=clock.monotonic)

    assert await mgr.get() == "SID-1"
    clock.advance(11)
    assert await mgr.get() == "SID-2"
    assert auth.calls == 2


async def test_invalidate__forces_reauth() -> None:
    auth = _Auth()
    clock = FakeClock()
    mgr = SessionManager(auth, ttl_seconds=10, monotonic=clock.monotonic)

    assert await mgr.get() == "SID-1"
    await mgr.invalidate()
    assert await mgr.get() == "SID-2"
    assert auth.calls == 2


async def test_get__single_flight_under_concurrency() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    calls = 0

    async def slow_auth() -> str:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return "SID"

    mgr = SessionManager(slow_auth, ttl_seconds=100)

    async def _run() -> str:
        return await mgr.get()

    tasks = [asyncio.create_task(_run()) for _ in range(5)]
    await started.wait()
    release.set()
    results = await asyncio.gather(*tasks)

    assert results == ["SID"] * 5
    assert calls == 1  # only one auth despite 5 concurrent callers
