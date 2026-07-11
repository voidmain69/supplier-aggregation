"""Offer ingestion on Postgres: price-changed event -> offer row. Integration."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from offer.adapters.models import OfferRow
from offer.events.handlers import build_price_changed_handler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


async def test_ingest_and_idempotency_on_postgres(
    pg_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(pg_session_factory)
    event = price_changed_event(offer_id="01J0000000000000000OFFER1", event_id="01JEVENTPG")

    await handler(event)
    await handler(event)  # redelivery -> idempotent

    async with pg_session_factory() as session:
        count = (await session.execute(select(func.count()).select_from(OfferRow))).scalar_one()
        row = await session.get(OfferRow, "01J0000000000000000OFFER1")
    assert count == 1
    assert row is not None
    assert row.price == Decimal("222.2200")
    assert row.price_uah == Decimal("9900.0000")
