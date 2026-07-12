"""GTIN auto-link on Postgres: discovered -> canonical + link + emitted event. Integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from matching.adapters.models import CanonicalProductRow
from matching.events.handlers import build_discovered_handler
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


async def test_gtin_auto_link_loop_on_postgres(
    pg_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(pg_session_factory)

    # two suppliers, same GTIN -> one canonical, two links, two events
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD1"))
    await handler(discovered_event(supplier_product_id="01J0000000000000000PROD2"))

    async with pg_session_factory() as session:
        count = (
            await session.execute(select(func.count()).select_from(CanonicalProductRow))
        ).scalar_one()
    assert count == 1

    publisher = InMemoryPublisher()
    assert await OutboxRelay(pg_session_factory, publisher).drain() == 2
    assert all(topic == "sa.matching.link" for topic, _k, _p in publisher.published)
    canonical_ids = {
        payload["data"]["canonical_product_id"] for _t, _k, payload in publisher.published
    }
    assert len(canonical_ids) == 1  # both link to the same canonical
