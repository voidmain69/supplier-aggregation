from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from connector_brain.adapters.identity_repo import resolve_and_stage
from connector_brain.sync import sync_offers
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_connector_sdk.dto import AccountCtx, RawOffer
from sa_core.money import Money

SessionFactory = async_sessionmaker[AsyncSession]

_ACCOUNT = AccountCtx(
    account_id="01J0000000000000000ACCT1",
    supplier_code="brain",
    credentials_ref="vault/brain/acc1",
    settlement_currency="USD",
)


def _offer(external_id: str, amount: str, currency: str = "USD") -> RawOffer:
    return RawOffer(
        external_id=external_id,
        price=Money.of(amount, currency),
        price_uah=Decimal("9900.00"),
        observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )


async def _discover(factory: SessionFactory, external_id: str) -> None:
    async with factory() as session, session.begin():
        await resolve_and_stage(
            session, supplier_code="brain", external_id=external_id, content_hash="h1"
        )


async def test_sync_offers__new_offer_emits_price_changed(
    sqlite_session_factory: SessionFactory,
) -> None:
    await _discover(sqlite_session_factory, "100463720")

    stats = await sync_offers(
        sqlite_session_factory,
        [_offer("100463720", "222.22")],
        supplier_code="brain",
        account=_ACCOUNT,
        sync_job_id="01JSYNC",
    )

    assert stats.changed == 1
    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1
    topic, _key, payload = publisher.published[0]
    assert topic == "sa.supplier.offer"
    assert payload["data"]["new_price"] == "222.2200"
    assert payload["data"]["old_price"] is None


async def test_sync_offers__unchanged_price_is_skipped(
    sqlite_session_factory: SessionFactory,
) -> None:
    await _discover(sqlite_session_factory, "100463720")
    offers = [_offer("100463720", "222.22")]
    await sync_offers(
        sqlite_session_factory, offers, supplier_code="brain", account=_ACCOUNT, sync_job_id="j1"
    )

    second = await sync_offers(
        sqlite_session_factory, offers, supplier_code="brain", account=_ACCOUNT, sync_job_id="j2"
    )

    assert second.changed == 0
    assert second.unchanged == 1


async def test_sync_offers__price_move_emits_with_old_price(
    sqlite_session_factory: SessionFactory,
) -> None:
    await _discover(sqlite_session_factory, "100463720")
    await sync_offers(
        sqlite_session_factory,
        [_offer("100463720", "222.22")],
        supplier_code="brain",
        account=_ACCOUNT,
        sync_job_id="j1",
    )

    stats = await sync_offers(
        sqlite_session_factory,
        [_offer("100463720", "250.00")],
        supplier_code="brain",
        account=_ACCOUNT,
        sync_job_id="j2",
    )

    assert stats.changed == 1
    publisher = InMemoryPublisher()
    await OutboxRelay(sqlite_session_factory, publisher).drain()
    # two events total (initial + change); the last one carries the previous price
    _topic, _key, payload = publisher.published[-1]
    assert payload["data"]["new_price"] == "250.0000"
    assert payload["data"]["old_price"] == "222.2200"


async def test_sync_offers__unknown_product_is_skipped(
    sqlite_session_factory: SessionFactory,
) -> None:
    stats = await sync_offers(
        sqlite_session_factory,
        [_offer("999", "10.00")],
        supplier_code="brain",
        account=_ACCOUNT,
        sync_job_id="j1",
    )
    assert stats.skipped == 1
    assert stats.changed == 0
