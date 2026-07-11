from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from catalog.db import create_schema
from sa_persistence.db import create_engine, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sa_core.events import make_cloud_event

SessionFactory = async_sessionmaker[AsyncSession]

_DATASCHEMA = "https://contracts.sa.internal/events/supplier.product.discovered.json"


@pytest.fixture
async def sqlite_session_factory() -> AsyncIterator[SessionFactory]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await create_schema(engine)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def pg_session_factory() -> AsyncIterator[SessionFactory]:
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", postgres.get_connection_url())
        engine = create_engine(dsn)
        await create_schema(engine)
        yield create_session_factory(engine)
        await engine.dispose()


@pytest.fixture
def discovered_event() -> Callable[..., dict[str, Any]]:
    """Factory building a valid supplier.product.discovered CloudEvent envelope."""

    def _make(
        *,
        supplier_product_id: str,
        external_id: str = "100463720",
        name: str = "ASUS TUF GAMING B850-PLUS WIFI",
        event_id: str | None = None,
    ) -> dict[str, Any]:
        envelope = make_cloud_event(
            type="supplier.product.discovered",
            source="//sa/connector-brain",
            subject=supplier_product_id,
            dataschema=_DATASCHEMA,
            data={
                "schema_version": 1,
                "supplier_product_id": supplier_product_id,
                "supplier_code": "brain",
                "external_id": external_id,
                "gtin": "04711387781609",
                "name": name,
                "brand": "ASUS",
                "attributes": {"Socket": "AM5"},
                "sync_job_id": "01J0000000000000000SYNC1",
            },
        )
        if event_id is not None:
            envelope["id"] = event_id
        return envelope

    return _make
