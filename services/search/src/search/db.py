"""Search database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/search/alembic.ini upgrade
head`` (or ``make migrate svc=search``), which additionally installs the pg_trgm GIN and
pgvector cosine indexes.
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from search.adapters.models import CanonicalDocumentRow, ProcessedEvent, SearchDocumentRow


async def create_schema(engine: AsyncEngine) -> None:
    """Create the search service's tables (search_document, canonical_document, processed_events).

    On Postgres the ``embedding`` columns are pgvector vectors, so the ``vector`` extension is
    enabled first. SQLite (unit tests) stores them as JSON instead.
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
            SearchDocumentRow.__table__,
            CanonicalDocumentRow.__table__,
            ProcessedEvent.__table__,
        ],
    )
