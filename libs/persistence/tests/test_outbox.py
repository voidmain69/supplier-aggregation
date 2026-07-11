from __future__ import annotations

from collections.abc import Callable

from sa_persistence.outbox import enqueue, fetch_unsent, mark_sent
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_core.events import OutboxRecord

SessionFactory = async_sessionmaker[AsyncSession]
MakeRecord = Callable[..., OutboxRecord]


async def _enqueue(factory: SessionFactory, record: OutboxRecord) -> None:
    async with factory() as session, session.begin():
        enqueue(session, record)


async def test_enqueue_persists_in_caller_transaction(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    await _enqueue(session_factory, make_record("01J000000000000000000000A"))

    async with session_factory() as session:
        rows = await fetch_unsent(session, limit=10)

    assert len(rows) == 1
    assert rows[0].topic == "sa.supplier.offer"
    assert rows[0].partition_key == "01J0000000000000000OFFER"
    assert rows[0].sent_at is None


async def test_enqueue_rolls_back_with_the_transaction(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    try:
        async with session_factory() as session, session.begin():
            enqueue(session, make_record("01J000000000000000000000B"))
            raise RuntimeError("business logic failed after staging the event")
    except RuntimeError:
        pass

    async with session_factory() as session:
        assert await fetch_unsent(session, limit=10) == []


async def test_relay_publishes_then_marks_sent(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    await _enqueue(session_factory, make_record("01J000000000000000000000A"))
    await _enqueue(session_factory, make_record("01J000000000000000000000B"))

    publisher = InMemoryPublisher()
    relay = OutboxRelay(session_factory, publisher)

    published = await relay.drain()
    assert published == 2
    assert {p[0] for p in publisher.published} == {"sa.supplier.offer"}

    # idempotent: everything already sent, so a second drain publishes nothing
    assert await relay.drain() == 0
    assert len(publisher.published) == 2


async def test_fetch_unsent_excludes_sent(
    session_factory: SessionFactory, make_record: MakeRecord
) -> None:
    await _enqueue(session_factory, make_record("01J000000000000000000000A"))

    async with session_factory() as session, session.begin():
        rows = await fetch_unsent(session, limit=10)
        await mark_sent(session, [rows[0].id])

    async with session_factory() as session:
        assert await fetch_unsent(session, limit=10) == []


async def test_mark_sent_empty_is_noop(session_factory: SessionFactory) -> None:
    async with session_factory() as session, session.begin():
        await mark_sent(session, [])  # must not raise
