from __future__ import annotations

import re
from collections.abc import AsyncIterator

import pytest
from sa_persistence.db import create_engine, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sync_orchestrator.db import create_schema
from sync_orchestrator.domain.schedule import AccountSchedule

SessionFactory = async_sessionmaker[AsyncSession]


@pytest.fixture
def schedule() -> AccountSchedule:
    return AccountSchedule(
        account_id="01J0000000000000000ACCT1",
        supplier_code="brain",
        credentials_ref="vault/brain/acc1",
        settlement_currency="USD",
        kind="all",
        interval_seconds=3600.0,
        mode="delta",
    )


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
