"""Price-history ingestion on Postgres: price-changed events -> points + stats. Integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from price_history.adapters.repository import price_stats
from price_history.events.handlers import build_price_changed_handler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]
_OFFER = "01J0000000000000000OFFER1"


async def test_ingest_and_stats_on_postgres(
    pg_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(pg_session_factory)
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
    await handler(  # redelivery of e2 -> idempotent
        price_changed_event(
            price_uah="9500.0000", observed_at="2026-07-11T11:00:00Z", event_id="e2"
        )
    )

    async with pg_session_factory() as session:
        stats = await price_stats(session, offer_id=_OFFER)
    assert stats["count"] == 2
    assert stats["min_uah"] == "9500.0000"
    assert stats["max_uah"] == "9900.0000"
    assert stats["last_uah"] == "9500.0000"
