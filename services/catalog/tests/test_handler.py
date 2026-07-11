from __future__ import annotations

from collections.abc import Callable
from typing import Any

from catalog.adapters.models import SupplierProductRow
from catalog.events.handlers import build_discovered_handler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _count(factory: SessionFactory) -> int:
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(SupplierProductRow))
        return int(result.scalar_one())


async def test_handler__ingests_discovered_product(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD1"))

    assert await _count(sqlite_session_factory) == 1


async def test_handler__is_idempotent_on_redelivery(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    event = discovered_event(supplier_product_id="01J0000000000000000PROD1", event_id="01JEVENT1")

    await handler(event)
    await handler(event)  # same event id -> skipped

    assert await _count(sqlite_session_factory) == 1


async def test_handler__new_event_for_same_product_updates(
    sqlite_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1", name="Old", event_id="01JEVENT1"
        )
    )
    await handler(
        discovered_event(
            supplier_product_id="01J0000000000000000PROD1", name="New", event_id="01JEVENT2"
        )
    )

    assert await _count(sqlite_session_factory) == 1
    async with sqlite_session_factory() as session:
        row = await session.get(SupplierProductRow, "01J0000000000000000PROD1")
    assert row is not None
    assert row.name == "New"
