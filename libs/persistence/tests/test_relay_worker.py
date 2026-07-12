"""RelayWorker: the long-lived poll loop around OutboxRelay.drain (SQLite, no broker)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from sa_persistence.outbox import enqueue
from sa_persistence.relay import InMemoryPublisher, OutboxRelay, RelayWorker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_core.events import OutboxRecord

SessionFactory = async_sessionmaker[AsyncSession]
MakeRecord = Callable[..., OutboxRecord]


async def _enqueue(factory: SessionFactory, record: OutboxRecord) -> None:
    async with factory() as session, session.begin():
        enqueue(session, record)


async def test_drain_all__empties_across_multiple_batches(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    for i in range(5):
        await _enqueue(session_factory, make_record(f"01J00000000000000000000{i:02d}"))

    publisher = InMemoryPublisher()
    worker = RelayWorker(OutboxRelay(session_factory, publisher), batch_size=2)

    total = await worker.drain_all()

    assert total == 5
    assert len(publisher.published) == 5
    assert await worker.drain_all() == 0  # nothing left


async def test_run__drains_then_stops_gracefully(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    await _enqueue(session_factory, make_record("01J000000000000000000000A"))
    await _enqueue(session_factory, make_record("01J000000000000000000000B"))

    publisher = InMemoryPublisher()
    worker = RelayWorker(OutboxRelay(session_factory, publisher), idle_delay=0.01)

    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)  # let it drain the backlog and enter the idle wait

    worker.stop()
    await asyncio.wait_for(task, timeout=1.0)  # wakes early on stop, not after idle_delay

    assert len(publisher.published) == 2


async def test_run__picks_up_events_enqueued_after_it_started(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    publisher = InMemoryPublisher()
    worker = RelayWorker(OutboxRelay(session_factory, publisher), idle_delay=0.01)

    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.03)  # starts against an empty outbox
    await _enqueue(session_factory, make_record("01J000000000000000000000A"))
    await asyncio.sleep(0.05)  # next poll tick picks it up

    worker.stop()
    await asyncio.wait_for(task, timeout=1.0)

    assert len(publisher.published) == 1
