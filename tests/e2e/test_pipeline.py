"""End-to-end: a Brain sync flows through the outbox relay, Kafka and every consumer.

This is the only test that wires the whole platform together, so it lives outside any
service (a service never imports another — hard rule 1). It proves the live pipeline:

    connector-brain sync -> outbox -> RelayWorker -> Kafka
        -> catalog   (supplier product)
        -> offer     (offer + best price)
        -> price-history (price point)
        -> matching  (GTIN auto-link) -> outbox -> RelayWorker -> Kafka
            -> catalog (canonical link)

Then it asserts, through each service's own repository, that the data actually landed.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from catalog.adapters.repository import canonical_ids_for, list_supplier_products
from catalog.db import create_schema as catalog_schema
from catalog.events.handlers import build_discovered_handler as catalog_discovered
from catalog.events.handlers import build_link_confirmed_handler as catalog_link
from connector_brain.db import create_schema as brain_schema
from connector_brain.sync import sync_offers, sync_products
from matching.db import create_schema as matching_schema
from matching.events.handlers import build_discovered_handler as matching_discovered
from offer.adapters.repository import best_offer_for_product
from offer.db import create_schema as offer_schema
from offer.events.handlers import build_price_changed_handler as offer_price
from price_history.adapters.repository import price_stats
from price_history.db import create_schema as price_history_schema
from price_history.events.handlers import build_price_changed_handler as ph_price
from sa_messaging import EventHandler, KafkaEventConsumer, KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.relay import OutboxRelay, RelayWorker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sa_connector_sdk.dto import AccountCtx, RawOffer, RawProduct
from sa_contracts import EVENT_REGISTRY
from sa_core.gtin import normalize_gtin
from sa_core.money import Money

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]

# Each service owns its own database inside the shared container (hard rule 1).
DATABASES = ("brain", "catalog", "offer", "matching", "pricehistory")

_DISCOVERED = "supplier.product.discovered"
_PRICE_CHANGED = "supplier.offer.price-changed"
_LINK_CONFIRMED = "matching.link.confirmed"


def dsn_for(base_async_url: str, database: str) -> str:
    """Point an asyncpg DSN at a different database on the same server."""
    head, _, _old = base_async_url.rpartition("/")
    return f"{head}/{database}"


_ACCOUNT = AccountCtx(
    account_id="01J0000000000000000ACCT1",
    supplier_code="brain",
    credentials_ref="vault/brain/acc1",
    settlement_currency="USD",
)


async def _create_databases(base_dsn: str) -> None:
    """Create one database per service (CREATE DATABASE needs autocommit)."""
    admin = create_async_engine(base_dsn, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            for name in DATABASES:
                await conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        await admin.dispose()


async def _drain_one(bootstrap: str, *, group: str, topic: str, handler: EventHandler) -> None:
    """Consume exactly one event on ``topic`` and run ``handler`` (bounded, with a timeout)."""
    consumer = KafkaEventConsumer(bootstrap, group_id=group, topics=[topic])
    async with consumer:
        await asyncio.wait_for(consumer.consume(handler, max_messages=1), timeout=30)


async def test_full_pipeline__brain_sync_reaches_every_service(
    pg_base_dsn: str, kafka_bootstrap: str
) -> None:
    await _create_databases(pg_base_dsn)

    async def factory(database: str, create_schema: object) -> SessionFactory:
        engine = create_engine(dsn_for(pg_base_dsn, database))
        await create_schema(engine)  # type: ignore[operator]
        return create_session_factory(engine)

    brain = await factory("brain", brain_schema)
    catalog = await factory("catalog", catalog_schema)
    offer = await factory("offer", offer_schema)
    matching = await factory("matching", matching_schema)
    price_history = await factory("pricehistory", price_history_schema)

    # --- 1. Brain sync stages discovered + price-changed events in its outbox ----------
    gtin = normalize_gtin("4711387781609")
    product = RawProduct(
        external_id="100463720",
        external_code="U1005797",
        articul="TUF GAMING B850-PLUS WIFI",
        name="ASUS TUF GAMING B850-PLUS WIFI",
        brand="ASUS",
        gtin=gtin,
        supplier_category_id="1264",
    )
    price_offer = RawOffer(
        external_id="100463720",
        price=Money(amount=Decimal("222.22"), currency="USD"),
        price_uah=Decimal("9900.0000"),
        observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )
    await sync_products(brain, [product], supplier_code="brain", sync_job_id="job-1")
    await sync_offers(
        brain, [price_offer], supplier_code="brain", account=_ACCOUNT, sync_job_id="job-1"
    )

    # --- 2. Relay brain's outbox to Kafka ---------------------------------------------
    async with KafkaPublisher(kafka_bootstrap) as pub:
        published = await RelayWorker(OutboxRelay(brain, pub)).drain_all()
    assert published == 2  # discovered + price-changed

    discovered_topic = EVENT_REGISTRY[_DISCOVERED].topic
    price_topic = EVENT_REGISTRY[_PRICE_CHANGED].topic
    link_topic = EVENT_REGISTRY[_LINK_CONFIRMED].topic

    # --- 3. Fan out to the consuming services -----------------------------------------
    await _drain_one(
        kafka_bootstrap,
        group="catalog.products",
        topic=discovered_topic,
        handler=catalog_discovered(catalog),
    )
    await _drain_one(
        kafka_bootstrap,
        group="matching.products",
        topic=discovered_topic,
        handler=matching_discovered(matching),
    )
    await _drain_one(
        kafka_bootstrap,
        group="offer.prices",
        topic=price_topic,
        handler=offer_price(offer),
    )
    await _drain_one(
        kafka_bootstrap,
        group="price-history.prices",
        topic=price_topic,
        handler=ph_price(price_history),
    )

    # --- 4. Matching auto-linked by GTIN; relay its link event, catalog consumes it ---
    async with KafkaPublisher(kafka_bootstrap) as pub:
        linked = await RelayWorker(OutboxRelay(matching, pub)).drain_all()
    assert linked == 1  # matching.link.confirmed
    await _drain_one(
        kafka_bootstrap,
        group="catalog.links",
        topic=link_topic,
        handler=catalog_link(catalog),
    )

    # --- 5. Every service ended up with the data ---------------------------------------
    async with catalog() as session:
        rows, _ = await list_supplier_products(session, supplier_code="brain")
        assert len(rows) == 1
        spid = rows[0].supplier_product_id
        canonicals = await canonical_ids_for(session, [spid])
    assert spid in canonicals  # canonical link closed the loop back into catalog

    async with offer() as session:
        best = await best_offer_for_product(session, spid)
    assert best is not None
    assert best.price_uah == Decimal("9900.0000")

    async with price_history() as session:
        stats = await price_stats(session, offer_id=best.offer_id)
    assert stats["count"] == 1
    assert stats["last_uah"] == "9900.0000"
