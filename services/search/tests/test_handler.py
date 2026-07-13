from __future__ import annotations

from collections.abc import Callable
from typing import Any

from search.adapters.models import SearchDocumentRow
from search.events.handlers import build_discovered_handler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _count(factory: SessionFactory) -> int:
    async with factory() as session:
        return len((await session.execute(select(SearchDocumentRow))).scalars().all())


async def test_handler__indexes_and_dedupes_by_event_id(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    handler = build_discovered_handler(sqlite_session_factory)
    event = discovered_event(supplier_product_id="01J00000000000000000000001")

    await handler(event)
    await handler(event)  # replay with the same event id — must be a no-op

    assert await _count(sqlite_session_factory) == 1
