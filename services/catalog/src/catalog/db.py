"""Catalog database wiring (schema create for tests/local; Alembic is a follow-up)."""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register the catalog tables on Base.metadata before create_all.
from catalog.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the catalog tables (supplier_product + processed_events)."""
    await create_all(engine)
