"""End-to-end ingestion on Postgres: Brain connector -> identity+outbox -> relay.

Marked integration (Docker only). Wires the real connector (over MockTransport HTTP) to a
real Postgres via testcontainers, proving the whole discovered-event loop and its
idempotency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connector_brain.sync import sync_products
from jsonschema.validators import Draft202012Validator
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]

REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCT_SCHEMA = json.loads(
    (REPO_ROOT / "contracts" / "events" / "supplier.product.discovered.json").read_text(
        encoding="utf-8"
    )
)


async def test_full_discovery_loop_on_postgres(build_connector, pg_session_factory) -> None:
    connector, _ = build_connector(page_size=10)
    page = await connector.fetch_products("1264", None)
    assert len(page.items) >= 1

    stats = await sync_products(
        pg_session_factory,
        page.items,
        supplier_code="brain",
        sync_job_id="01J0000000000000000SYNC1",
    )
    assert stats.discovered == len(page.items)

    publisher = InMemoryPublisher()
    published = await OutboxRelay(pg_session_factory, publisher).drain()
    assert published == stats.discovered

    topic, key, payload = publisher.published[0]
    assert topic == "sa.supplier.product"
    Draft202012Validator(PRODUCT_SCHEMA).validate(payload["data"])
    assert payload["subject"] == key  # keyed by supplier_product_id

    # Re-run the same sync: identity is known, so no new events are produced.
    stats2 = await sync_products(
        pg_session_factory,
        page.items,
        supplier_code="brain",
        sync_job_id="01J0000000000000000SYNC2",
    )
    assert stats2.discovered == 0
    assert await OutboxRelay(pg_session_factory, publisher).drain() == 0
