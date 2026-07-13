"""Daily price rollup (portable GROUP BY): repository + API."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from price_history.adapters.repository import append_price_point, daily_price_stats
from price_history.api.deps import get_session_factory
from price_history.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged

SessionFactory = async_sessionmaker[AsyncSession]
_OFFER = "01J0000000000000000OFFER1"


def _point(price_uah: str, *, day: int, hour: int) -> SupplierOfferPriceChanged:
    return SupplierOfferPriceChanged(
        schema_version=1,
        offer_id=_OFFER,
        supplier_account_id="01J0000000000000000ACCT1",
        supplier_product_id="01J0000000000000000PROD1",
        new_price="222.2200",
        currency="USD",
        price_uah=price_uah,
        observed_at=datetime(2026, 7, day, hour, 0, tzinfo=UTC),
        sync_job_id="01JSYNC",
    )


async def _seed(factory: SessionFactory) -> None:
    async with factory() as session, session.begin():
        # Day 11: 9900 (10:00), 9500 (12:00)  ->  min 9500, max 9900, last 9500
        await append_price_point(session, _point("9900.0000", day=11, hour=10))
        await append_price_point(session, _point("9500.0000", day=11, hour=12))
        # Day 12: 9700 (09:00)  ->  single point
        await append_price_point(session, _point("9700.0000", day=12, hour=9))


async def test_daily__buckets_min_max_avg_last(sqlite_session_factory: SessionFactory) -> None:
    await _seed(sqlite_session_factory)
    async with sqlite_session_factory() as session:
        days = await daily_price_stats(session, offer_id=_OFFER)

    assert [d["day"] for d in days] == ["2026-07-11", "2026-07-12"]
    d11, d12 = days
    assert (d11["count"], d11["min_uah"], d11["max_uah"], d11["last_uah"]) == (
        2,
        "9500.0000",
        "9900.0000",
        "9500.0000",  # 12:00 is the day's latest point
    )
    assert d11["avg_uah"] == "9700.0000"
    assert (d12["count"], d12["min_uah"], d12["last_uah"]) == (1, "9700.0000", "9700.0000")


async def test_daily__empty_offer(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session:
        assert await daily_price_stats(session, offer_id="nope") == []


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_daily_endpoint__returns_buckets(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(sqlite_session_factory)
    async with client:
        resp = await client.get("/v1/price-history/daily", params={"offer_id": _OFFER})
    assert resp.status_code == 200
    body: list[dict[str, Any]] = resp.json()
    assert [b["day"] for b in body] == ["2026-07-11", "2026-07-12"]
    assert body[0]["max_uah"] == "9900.0000"
