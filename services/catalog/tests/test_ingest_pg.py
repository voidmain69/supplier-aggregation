"""Catalog ingestion on Postgres: discovered event -> supplier_product row. Integration."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from catalog.adapters.models import SupplierProductRow
from catalog.events.handlers import build_discovered_handler
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


async def _count(factory: SessionFactory) -> int:
    async with factory() as session:
        result = await session.execute(select(func.count()).select_from(SupplierProductRow))
        return int(result.scalar_one())


async def test_ingest_and_idempotency_on_postgres(
    pg_session_factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_discovered_handler(pg_session_factory)
    event = discovered_event(supplier_product_id="01J0000000000000000PROD1", event_id="01JEVENTPG")

    await handler(event)
    await handler(event)  # redelivery -> idempotent

    assert await _count(pg_session_factory) == 1
    async with pg_session_factory() as session:
        row = await session.get(SupplierProductRow, "01J0000000000000000PROD1")
    assert row is not None
    assert row.gtin == "04711387781609"
    assert row.supplier_code == "brain"
