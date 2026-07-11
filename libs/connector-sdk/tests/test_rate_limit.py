from __future__ import annotations

import pytest

from sa_connector_sdk.rate_limit import AsyncTokenBucket
from sa_connector_sdk.testkit import FakeClock


def _bucket(
    clock: FakeClock, *, rate: float = 3.0, capacity: float | None = None
) -> AsyncTokenBucket:
    return AsyncTokenBucket(
        rate=rate, capacity=capacity, monotonic=clock.monotonic, sleep=clock.sleep
    )


async def test_acquire__within_capacity__no_wait() -> None:
    clock = FakeClock()
    bucket = _bucket(clock)  # 3 tokens available
    for _ in range(3):
        await bucket.acquire()
    assert clock.monotonic() == 0.0


async def test_acquire__over_capacity__sleeps_to_refill() -> None:
    clock = FakeClock()
    bucket = _bucket(clock)  # rate 3/s, capacity 3
    for _ in range(3):
        await bucket.acquire()
    await bucket.acquire()  # empty bucket → must wait 1/3 s for one token
    assert clock.monotonic() == pytest.approx(1 / 3)


async def test_acquire__sustained_rate__matches_budget() -> None:
    clock = FakeClock()
    bucket = _bucket(clock)  # 3 req/s
    for _ in range(9):
        await bucket.acquire()
    # first 3 free, remaining 6 at 3/s = 2.0 s
    assert clock.monotonic() == pytest.approx(2.0)


async def test_acquire__more_than_capacity__raises() -> None:
    bucket = AsyncTokenBucket(rate=3.0)
    with pytest.raises(ValueError, match="capacity"):
        await bucket.acquire(10)


def test_bucket__non_positive_rate__raises() -> None:
    with pytest.raises(ValueError, match="rate must be positive"):
        AsyncTokenBucket(rate=0)
