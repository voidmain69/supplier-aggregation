from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from price_history.adapters.models import PricePointRow
from price_history.api.deps import get_session_factory
from price_history.events.handlers import build_price_changed_handler
from price_history.main import create_app
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]
_OFFER = "01J0000000000000000OFFER1"


async def _count(factory: SessionFactory) -> int:
    async with factory() as session:
        return int(
            (await session.execute(select(func.count()).select_from(PricePointRow))).scalar_one()
        )


async def test_handler__appends_and_is_idempotent(
    sqlite_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(sqlite_session_factory)
    event = price_changed_event(event_id="01JEVENT1")
    await handler(event)
    await handler(event)  # redelivery -> idempotent
    assert await _count(sqlite_session_factory) == 1


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _ingest(
    factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(factory)
    await handler(
        price_changed_event(
            price_uah="9900.0000", observed_at="2026-07-11T10:00:00Z", event_id="e1"
        )
    )
    await handler(
        price_changed_event(
            price_uah="9500.0000", observed_at="2026-07-11T11:00:00Z", event_id="e2"
        )
    )


async def test_api__history_and_stats(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    price_changed_event: Callable[..., dict[str, Any]],
) -> None:
    await _ingest(sqlite_session_factory, price_changed_event)
    async with client:
        history = (await client.get("/v1/price-history", params={"offer_id": _OFFER})).json()
        assert [p["price_uah"] for p in history["items"]] == ["9900.0000", "9500.0000"]

        stats = (await client.get("/v1/price-history/stats", params={"offer_id": _OFFER})).json()
        assert stats["count"] == 2
        assert stats["min_uah"] == "9500.0000"
        assert stats["last_uah"] == "9500.0000"
