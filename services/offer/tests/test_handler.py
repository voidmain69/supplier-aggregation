from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from offer.adapters.models import OfferRow
from offer.events.handlers import build_price_changed_handler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _count(factory: SessionFactory) -> int:
    async with factory() as session:
        return int((await session.execute(select(func.count()).select_from(OfferRow))).scalar_one())


async def test_handler__ingests_offer(
    sqlite_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(sqlite_session_factory)
    await handler(price_changed_event(offer_id="01J0000000000000000OFFER1"))
    assert await _count(sqlite_session_factory) == 1


async def test_handler__idempotent_on_redelivery(
    sqlite_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(sqlite_session_factory)
    event = price_changed_event(offer_id="01J0000000000000000OFFER1", event_id="01JEVENT1")
    await handler(event)
    await handler(event)
    assert await _count(sqlite_session_factory) == 1


async def test_handler__price_change_updates_offer(
    sqlite_session_factory: SessionFactory, price_changed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_price_changed_handler(sqlite_session_factory)
    await handler(
        price_changed_event(
            offer_id="01J0000000000000000OFFER1", new_price="222.2200", event_id="01JEVENT1"
        )
    )
    await handler(
        price_changed_event(
            offer_id="01J0000000000000000OFFER1", new_price="250.0000", event_id="01JEVENT2"
        )
    )

    async with sqlite_session_factory() as session:
        row = await session.get(OfferRow, "01J0000000000000000OFFER1")
    assert row is not None
    assert row.price == Decimal("250.0000")
