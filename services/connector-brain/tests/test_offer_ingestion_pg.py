"""Offer emission on Postgres: discover product -> sync offer -> price-changed in outbox."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from connector_brain.adapters.identity_repo import resolve_and_stage
from connector_brain.sync import sync_offers
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_connector_sdk.dto import AccountCtx, RawOffer
from sa_core.money import Money

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]

_ACCOUNT = AccountCtx(
    account_id="01J0000000000000000ACCT1",
    supplier_code="brain",
    credentials_ref="vault/brain/acc1",
    settlement_currency="USD",
)


async def test_offer_price_changed_loop_on_postgres(pg_session_factory: SessionFactory) -> None:
    async with pg_session_factory() as session, session.begin():
        await resolve_and_stage(
            session, supplier_code="brain", external_id="100463720", content_hash="h1"
        )

    offer = RawOffer(
        external_id="100463720",
        price=Money.of("222.22", "USD"),
        price_uah=Decimal("9900.00"),
        observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )
    stats = await sync_offers(
        pg_session_factory, [offer], supplier_code="brain", account=_ACCOUNT, sync_job_id="01JSYNC"
    )
    assert stats.changed == 1

    publisher = InMemoryPublisher()
    assert await OutboxRelay(pg_session_factory, publisher).drain() == 1
    topic, key, payload = publisher.published[0]
    assert topic == "sa.supplier.offer"
    assert payload["subject"] == key
    assert payload["data"]["new_price"] == "222.2200"

    # re-sync same price -> no new event
    again = await sync_offers(
        pg_session_factory, [offer], supplier_code="brain", account=_ACCOUNT, sync_job_id="01JSYNC2"
    )
    assert again.changed == 0
    assert await OutboxRelay(pg_session_factory, publisher).drain() == 0
