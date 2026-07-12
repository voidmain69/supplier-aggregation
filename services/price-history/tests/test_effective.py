"""Effective-price point ingestion (append + handler idempotency)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from price_history.adapters.models import EffectivePricePointRow
from price_history.adapters.repository import append_effective_point
from price_history.events.handlers import build_effective_price_changed_handler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.offer_effective_price_changed import OfferEffectivePriceChanged
from sa_core.events import make_cloud_event

SessionFactory = async_sessionmaker[AsyncSession]
_OFFER = "01J0000000000000000OFFER1"


def _event(
    new_effective: str, *, hour: int, cause: str = "price_changed"
) -> OfferEffectivePriceChanged:
    return OfferEffectivePriceChanged(
        schema_version=1,
        offer_id=_OFFER,
        supplier_account_id="01J0000000000000000ACCT1",
        supplier_product_id="01J0000000000000000PROD1",
        old_effective_price_uah=None,
        new_effective_price_uah=new_effective,
        base_price="222.2200",
        currency="USD",
        observed_at=datetime(2026, 7, 11, hour, 0, tzinfo=UTC),
        cause=cause,
    )


async def _rows(factory: SessionFactory) -> list[EffectivePricePointRow]:
    async with factory() as session:
        return list((await session.execute(select(EffectivePricePointRow))).scalars().all())


async def test_append_effective__stores_row(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await append_effective_point(session, _event("945.0000", hour=10))

    rows = await _rows(sqlite_session_factory)
    assert len(rows) == 1
    assert rows[0].effective_price_uah == Decimal("945.0000")
    assert rows[0].base_price == Decimal("222.2200")
    assert rows[0].cause == "price_changed"


async def test_append_effective__idempotent_on_offer_ts(
    sqlite_session_factory: SessionFactory,
) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await append_effective_point(session, _event("945.0000", hour=10))
        await append_effective_point(session, _event("800.0000", hour=10))  # same ts -> ignored
    rows = await _rows(sqlite_session_factory)
    assert len(rows) == 1
    assert rows[0].effective_price_uah == Decimal("945.0000")


async def test_handler__dedupes_by_event_id(sqlite_session_factory: SessionFactory) -> None:
    handler = build_effective_price_changed_handler(sqlite_session_factory)
    envelope: dict[str, Any] = make_cloud_event(
        type="offer.effective-price.changed",
        source="//sa/offer",
        subject=_OFFER,
        dataschema="https://contracts.sa.internal/events/offer.effective-price.changed.json",
        data=_event("945.0000", hour=10).model_dump(mode="json"),
    )
    await handler(envelope)
    await handler(envelope)  # replay — must be a no-op

    assert len(await _rows(sqlite_session_factory)) == 1
