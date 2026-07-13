"""Offer database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/offer/alembic.ini upgrade
head`` (or ``make migrate svc=offer``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

from offer.adapters.models import OfferRow, ProcessedEvent, SupplierAccountRow


async def create_schema(engine: AsyncEngine) -> None:
    """Create the offer's own tables (offer + supplier_account + offer_processed_events)."""
    await create_all(
        engine,
        tables=[
            OfferRow.__table__,
            SupplierAccountRow.__table__,
            ProcessedEvent.__table__,
        ],
    )
