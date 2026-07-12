"""Async SQLAlchemy engine/session helpers and the declarative base.

Services build their own tables on :class:`Base` and get an async session factory from
:func:`create_session_factory`. Kept thin — connection tuning and migrations (Alembic)
live in the service; this is just the shared wiring.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from sqlalchemy import FromClause, Table
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by all persistence models."""


def create_engine(dsn: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async engine. ``dsn`` e.g. ``postgresql+asyncpg://...``."""
    return create_async_engine(dsn, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build an async session factory bound to ``engine``."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all(engine: AsyncEngine, *, tables: Sequence[FromClause] | None = None) -> None:
    """Create tables on :class:`Base` (tests/local; prod uses Alembic).

    A service passes its own model ``__table__`` objects to create only its tables — the
    shared ``Base.metadata`` holds every service's tables in one process (e.g. the test
    suite), so an unscoped create_all would build another service's tables here.
    """
    scoped = cast("Sequence[Table] | None", tables)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=scoped)
