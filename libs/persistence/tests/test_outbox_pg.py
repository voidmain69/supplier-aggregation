"""Postgres-backed outbox tests (real SKIP LOCKED). Marked integration — CI + Docker only."""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

import pytest
from sa_persistence.db import create_all, create_engine, create_session_factory
from sa_persistence.outbox import enqueue
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_core.events import OutboxRecord

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


@pytest.fixture
async def pg_session_factory() -> AsyncIterator[SessionFactory]:
    # Imported lazily so unit-only runs (and envs without Docker) don't need testcontainers.
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", postgres.get_connection_url())
        engine = create_engine(dsn)
        await create_all(engine)
        yield create_session_factory(engine)
        await engine.dispose()


def _record(record_id: str) -> OutboxRecord:
    envelope = {
        "specversion": "1.0",
        "id": record_id,
        "source": "//sa/connector-brain",
        "type": "supplier.offer.price-changed",
        "time": "2026-07-11T10:00:00Z",
        "subject": "01J0000000000000000OFFER",
        "dataschema": "https://contracts.sa.internal/events/supplier.offer.price-changed.json",
        "data": {"offer_id": "01J0000000000000000OFFER", "new_price": "9900.0000"},
    }
    return OutboxRecord.for_event(topic="sa.supplier.offer", envelope=envelope)


async def _enqueue(factory: SessionFactory, record: OutboxRecord) -> None:
    async with factory() as session, session.begin():
        enqueue(session, record)


async def test_outbox_roundtrip_on_postgres(pg_session_factory: SessionFactory) -> None:
    await _enqueue(pg_session_factory, _record("01J00000000000000000000PG1"))
    await _enqueue(pg_session_factory, _record("01J00000000000000000000PG2"))

    publisher = InMemoryPublisher()
    relay = OutboxRelay(pg_session_factory, publisher)

    assert await relay.drain() == 2
    assert await relay.drain() == 0
    assert len(publisher.published) == 2


async def test_concurrent_relays_do_not_double_publish(
    pg_session_factory: SessionFactory,
) -> None:
    ids = [f"01J0000000000000000000PG{i:02d}" for i in range(10)]
    for record_id in ids:
        await _enqueue(pg_session_factory, _record(record_id))

    left, right = InMemoryPublisher(), InMemoryPublisher()
    # Small batches so both relays race for rows; SKIP LOCKED must prevent overlap.
    results = await asyncio.gather(
        OutboxRelay(pg_session_factory, left).drain(batch_size=3),
        OutboxRelay(pg_session_factory, right).drain(batch_size=3),
    )

    all_keys = [p[1] for p in (*left.published, *right.published)]
    assert sum(results) == len(all_keys)  # no row published by both relays
