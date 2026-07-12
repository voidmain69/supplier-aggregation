from __future__ import annotations

from datetime import UTC, datetime

from price_history.adapters.repository import (
    append_price_point,
    list_price_points,
    price_stats,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged

SessionFactory = async_sessionmaker[AsyncSession]
_OFFER = "01J0000000000000000OFFER1"


def _point(price_uah: str, *, hour: int) -> SupplierOfferPriceChanged:
    return SupplierOfferPriceChanged(
        schema_version=1,
        offer_id=_OFFER,
        supplier_account_id="01J0000000000000000ACCT1",
        supplier_product_id="01J0000000000000000PROD1",
        new_price="222.2200",
        currency="USD",
        price_uah=price_uah,
        observed_at=datetime(2026, 7, 11, hour, 0, tzinfo=UTC),
        sync_job_id="01JSYNC",
    )


async def _seed(factory: SessionFactory) -> None:
    async with factory() as session, session.begin():
        await append_price_point(session, _point("9900.0000", hour=10))
        await append_price_point(session, _point("9500.0000", hour=11))
        await append_price_point(session, _point("9700.0000", hour=12))


async def test_append__idempotent_on_offer_ts(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await append_price_point(session, _point("9900.0000", hour=10))
        await append_price_point(session, _point("8888.0000", hour=10))  # same ts -> ignored

    async with sqlite_session_factory() as session:
        rows, _ = await list_price_points(session, offer_id=_OFFER)
    assert len(rows) == 1
    assert str(rows[0].price_uah) == "9900.0000"


async def test_list__ordered_and_cursor(sqlite_session_factory: SessionFactory) -> None:
    await _seed(sqlite_session_factory)
    async with sqlite_session_factory() as session:
        page1, cursor = await list_price_points(session, offer_id=_OFFER, limit=2)
        assert [str(r.price_uah) for r in page1] == ["9900.0000", "9500.0000"]
        assert cursor is not None
        page2, cursor2 = await list_price_points(session, offer_id=_OFFER, cursor=cursor, limit=2)
        assert [str(r.price_uah) for r in page2] == ["9700.0000"]
        assert cursor2 is None


async def test_list__range_filter(sqlite_session_factory: SessionFactory) -> None:
    await _seed(sqlite_session_factory)
    async with sqlite_session_factory() as session:
        rows, _ = await list_price_points(
            session,
            offer_id=_OFFER,
            from_ts=datetime(2026, 7, 11, 11, 0, tzinfo=UTC),
            to_ts=datetime(2026, 7, 11, 11, 30, tzinfo=UTC),
        )
    assert [str(r.price_uah) for r in rows] == ["9500.0000"]


async def test_stats__min_max_avg_last(sqlite_session_factory: SessionFactory) -> None:
    await _seed(sqlite_session_factory)
    async with sqlite_session_factory() as session:
        stats = await price_stats(session, offer_id=_OFFER)
    assert stats["count"] == 3
    assert stats["min_uah"] == "9500.0000"
    assert stats["max_uah"] == "9900.0000"
    assert stats["avg_uah"] == "9700.0000"
    assert stats["last_uah"] == "9700.0000"  # hour=12 is most recent


async def test_stats__empty(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session:
        stats = await price_stats(session, offer_id="nope")
    assert stats["count"] == 0
    assert stats["min_uah"] is None
    assert stats["last_ts"] is None
