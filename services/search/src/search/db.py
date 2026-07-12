"""Search database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/search/alembic.ini upgrade
head`` (or ``make migrate svc=search``), which additionally installs the pg_trgm GIN index.
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

from search.adapters.models import ProcessedEvent, SearchDocumentRow


async def create_schema(engine: AsyncEngine) -> None:
    """Create the search service's own tables (search_document + processed_events)."""
    await create_all(
        engine,
        tables=[SearchDocumentRow.__table__, ProcessedEvent.__table__],
    )
