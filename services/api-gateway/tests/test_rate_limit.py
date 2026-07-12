"""Token-bucket rate limiter (deterministic via an injected clock)."""

from __future__ import annotations

from api_gateway.domain.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allow__spends_burst_then_denies() -> None:
    clock = FakeClock()
    limiter = RateLimiter(rate_per_second=1.0, burst=2, clock=clock)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False  # burst exhausted, no time passed


def test_allow__refills_over_time() -> None:
    clock = FakeClock()
    limiter = RateLimiter(rate_per_second=1.0, burst=1, clock=clock)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    clock.advance(1.0)  # one token refilled
    assert limiter.allow("a") is True


def test_allow__is_per_key() -> None:
    clock = FakeClock()
    limiter = RateLimiter(rate_per_second=1.0, burst=1, clock=clock)

    assert limiter.allow("a") is True
    assert limiter.allow("b") is True  # different principal, own bucket
    assert limiter.allow("a") is False


def test_retry_after__reports_seconds_until_a_token() -> None:
    clock = FakeClock()
    limiter = RateLimiter(rate_per_second=0.5, burst=1, clock=clock)

    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    assert limiter.retry_after("a") == 2  # 1 token / 0.5 per sec
