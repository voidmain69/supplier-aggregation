from __future__ import annotations

from collections.abc import Callable
from typing import Any

from matching.adapters.models import CanonicalProductRow, ProductLinkRow
from matching.adapters.repository import get_link
from matching.events.handlers import build_discovered_handler
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _canonical_count(factory: SessionFactory) -> int:
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(CanonicalProductRow))
        return int(result.scalar_one())


async def test_handler__gtin_creates_canonical_and_link_and_emits(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD1"))

    assert await _canonical_count(sqlite_session_factory) == 1
    async with sqlite_session_factory() as session:
        link = await get_link(session, "01J0000000000000000PROD1")
    assert link is not None
    assert link.method == "gtin_auto"
    assert link.confidence == 1.0

    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1
    topic, _key, payload = publisher.published[0]
    assert topic == "sa.matching.link"
    assert payload["data"]["method"] == "gtin_auto"
    assert payload["data"]["canonical_product_id"] == link.canonical_product_id


async def test_handler__same_gtin_links_to_same_canonical(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD1"))
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD2"))

    assert await _canonical_count(sqlite_session_factory) == 1  # one canonical for the GTIN
    async with sqlite_session_factory() as session:
        link1 = await get_link(session, "01J0000000000000000PROD1")
        link2 = await get_link(session, "01J0000000000000000PROD2")
    assert link1 is not None and link2 is not None
    assert link1.canonical_product_id == link2.canonical_product_id


async def test_handler__no_gtin_is_skipped(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD1", gtin=None))

    assert await _canonical_count(sqlite_session_factory) == 0
    async with sqlite_session_factory() as session:
        assert await get_link(session, "01J0000000000000000PROD1") is None
        # no event emitted
        rows = await session.execute(select(func.count()).select_from(ProductLinkRow))
        assert rows.scalar_one() == 0


async def test_handler__idempotent_on_redelivery(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    event = discovered_event(supplier_product_id="01J0000000000000000PROD1", event_id="01JEVENT1")
    await handler(event)
    await handler(event)

    assert await _canonical_count(sqlite_session_factory) == 1
    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1  # emitted once
