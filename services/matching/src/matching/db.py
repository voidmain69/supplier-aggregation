"""Matching database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/matching/alembic.ini upgrade
head`` (or ``make migrate svc=matching``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from matching.adapters.models import CanonicalProductRow, ProcessedEvent, ProductLinkRow


async def create_schema(engine: AsyncEngine) -> None:
    """Create matching's own tables (canonical_product, product_link, processed, outbox).

    On Postgres the ``canonical_product.embedding`` column is a pgvector vector, so the
    ``vector`` extension is enabled first. SQLite (unit tests) stores it as JSON instead.
    """
    if engine.dialect.name == "postgresql":
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Drop pooled connections: asyncpg caches type introspection per connection, so a
        # connection open before `vector` existed would not see the new type in create_all.
        await engine.dispose()
    await create_all(
        engine,
        tables=[
            CanonicalProductRow.__table__,
            ProductLinkRow.__table__,
            ProcessedEvent.__table__,
            OutboxRow.__table__,
        ],
    )
