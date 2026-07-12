"""Catalog database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/catalog/alembic.ini upgrade
head`` (or ``make migrate svc=catalog``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register the catalog tables on Base.metadata before create_all.
from catalog.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the catalog tables (supplier_product + processed_events)."""
    await create_all(engine)
