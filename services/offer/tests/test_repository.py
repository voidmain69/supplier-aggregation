from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from offer.adapters.repository import (
    best_offer_for_product,
    get_offer,
    list_offers_for_product,
    upsert_account_terms,
    upsert_offer,
)
from offer.domain.pricing import FinancialTerms
from sa_persistence.outbox import fetch_unsent
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged

SessionFactory = async_sessionmaker[AsyncSession]


async def _outbox_events(factory: SessionFactory) -> list[dict]:
    async with factory() as session:
        rows = await fetch_unsent(session, limit=100)
        return [r.payload for r in rows]


def _payload(
    offer_id: str,
    *,
    supplier_product_id: str = "01J0000000000000000PROD1",
    account: str = "01J0000000000000000ACCT1",
    new_price: str = "222.2200",
    price_uah: str | None = "9900.0000",
) -> SupplierOfferPriceChanged:
    return SupplierOfferPriceChanged(
        schema_version=1,
        offer_id=offer_id,
        supplier_account_id=account,
        supplier_product_id=supplier_product_id,
        new_price=new_price,
        currency="USD",
        price_uah=price_uah,
        observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
        sync_job_id="01JSYNC",
    )


async def test_upsert__insert_then_update_price(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J0000000000000000OFFER1", new_price="222.2200"))
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J0000000000000000OFFER1", new_price="250.0000"))

    async with sqlite_session_factory() as session:
        row = await get_offer(session, "01J0000000000000000OFFER1")
    assert row is not None
    assert row.price == Decimal("250.0000")


async def test_list_offers_for_product__cursor(sqlite_session_factory: SessionFactory) -> None:
    ids = ["01J000000000000000OFFER01", "01J000000000000000OFFER02", "01J000000000000000OFFER03"]
    async with sqlite_session_factory() as session, session.begin():
        for i, oid in enumerate(ids):
            await upsert_offer(session, _payload(oid, account=f"01J0000000000000000ACCT{i}"))

    async with sqlite_session_factory() as session:
        page1, cursor = await list_offers_for_product(session, "01J0000000000000000PROD1", limit=2)
        assert [o.offer_id for o in page1] == ids[:2]
        assert cursor is not None
        page2, cursor2 = await list_offers_for_product(
            session, "01J0000000000000000PROD1", cursor=cursor, limit=2
        )
        assert [o.offer_id for o in page2] == ids[2:]
        assert cursor2 is None


async def test_best_offer__cheapest_by_uah(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(
            session, _payload("01J000000000000000OFFER01", account="a1", price_uah="9900.0000")
        )
        await upsert_offer(
            session, _payload("01J000000000000000OFFER02", account="a2", price_uah="9500.0000")
        )
        await upsert_offer(
            session, _payload("01J000000000000000OFFER03", account="a3", price_uah=None)
        )

    async with sqlite_session_factory() as session:
        best = await best_offer_for_product(session, "01J0000000000000000PROD1")
    assert best is not None
    assert best.offer_id == "01J000000000000000OFFER02"  # 9500 is cheapest; null excluded


async def test_best_offer__none_when_no_uah_price(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J000000000000000OFFER01", price_uah=None))
    async with sqlite_session_factory() as session:
        assert await best_offer_for_product(session, "01J0000000000000000PROD1") is None


async def test_upsert__uses_account_terms_for_effective_price(
    sqlite_session_factory: SessionFactory,
) -> None:
    account = "01J0000000000000000ACCT1"
    async with sqlite_session_factory() as session, session.begin():
        # 10% discount and an explicit FX rate: 10 USD * 41.5 * 0.90 = 373.5 UAH
        await upsert_account_terms(
            session,
            account,
            FinancialTerms(discount_pct=Decimal("0.10"), fx_rate_to_uah=Decimal("41.5")),
        )
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(
            session,
            _payload(
                "01J000000000000000OFFER01", account=account, new_price="10.0000", price_uah=None
            ),
        )
    async with sqlite_session_factory() as session:
        row = await get_offer(session, "01J000000000000000OFFER01")
    assert row is not None
    assert row.effective_price_uah == Decimal("373.5000")


async def test_upsert_account_terms__reprices_existing_offers(
    sqlite_session_factory: SessionFactory,
) -> None:
    account = "01J0000000000000000ACCT1"
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(
            session, _payload("01J000000000000000OFFER01", account=account, price_uah="1000.0000")
        )
    # No terms yet: USD with no FX falls back to supplier price_uah = 1000.
    async with sqlite_session_factory() as session:
        row = await get_offer(session, "01J000000000000000OFFER01")
        assert row is not None and row.effective_price_uah == Decimal("1000.0000")

    async with sqlite_session_factory() as session, session.begin():
        count = await upsert_account_terms(
            session, account, FinancialTerms(discount_pct=Decimal("0.20"))
        )
    assert count == 1
    async with sqlite_session_factory() as session:
        row = await get_offer(session, "01J000000000000000OFFER01")
    assert row is not None
    assert row.effective_price_uah == Decimal("800.0000")  # 1000 * 0.80


async def test_best_offer__ranks_by_effective_not_raw_uah(
    sqlite_session_factory: SessionFactory,
) -> None:
    # Two offers with the same raw UAH price; a discount on account a1 makes it the real cheapest.
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(
            session, _payload("01J000000000000000OFFER01", account="a1", price_uah="1000.0000")
        )
        await upsert_offer(
            session, _payload("01J000000000000000OFFER02", account="a2", price_uah="1000.0000")
        )
        await upsert_account_terms(session, "a1", FinancialTerms(discount_pct=Decimal("0.30")))

    async with sqlite_session_factory() as session:
        best = await best_offer_for_product(session, "01J0000000000000000PROD1")
    assert best is not None
    assert best.offer_id == "01J000000000000000OFFER01"  # 700 effective beats 1000


async def test_upsert__emits_effective_price_changed_event(
    sqlite_session_factory: SessionFactory,
) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J000000000000000OFFER01", price_uah="1000.0000"))
    events = await _outbox_events(sqlite_session_factory)
    assert len(events) == 1
    data = events[0]["data"]
    assert events[0]["type"] == "offer.effective-price.changed"
    assert data["offer_id"] == "01J000000000000000OFFER01"
    assert data["new_effective_price_uah"] == "1000.0000"
    assert data["old_effective_price_uah"] is None
    assert data["cause"] == "price_changed"


async def test_upsert__no_event_when_effective_unchanged(
    sqlite_session_factory: SessionFactory,
) -> None:
    # Same price twice: the second upsert must not emit (effective did not move).
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J000000000000000OFFER01", price_uah="1000.0000"))
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(session, _payload("01J000000000000000OFFER01", price_uah="1000.0000"))
    assert len(await _outbox_events(sqlite_session_factory)) == 1


async def test_upsert_account_terms__emits_terms_changed_events(
    sqlite_session_factory: SessionFactory,
) -> None:
    account = "01J0000000000000000ACCT1"
    async with sqlite_session_factory() as session, session.begin():
        await upsert_offer(
            session, _payload("01J000000000000000OFFER01", account=account, price_uah="1000.0000")
        )
    async with sqlite_session_factory() as session, session.begin():
        await upsert_account_terms(session, account, FinancialTerms(discount_pct=Decimal("0.20")))

    events = await _outbox_events(sqlite_session_factory)
    terms_events = [e for e in events if e["data"]["cause"] == "terms_changed"]
    assert len(terms_events) == 1
    assert terms_events[0]["data"]["new_effective_price_uah"] == "800.0000"
    assert terms_events[0]["data"]["old_effective_price_uah"] == "1000.0000"
