"""Catalog database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/catalog/alembic.ini upgrade
head`` (or ``make migrate svc=catalog``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

from catalog.adapters.models import ProcessedEvent, ProductCanonicalLink, SupplierProductRow


async def create_schema(engine: AsyncEngine) -> None:
    """Create the catalog's own tables (supplier_product, canonical link, processed_events)."""
    await create_all(
        engine,
        tables=[
            SupplierProductRow.__table__,
            ProductCanonicalLink.__table__,
            ProcessedEvent.__table__,
        ],
    )
