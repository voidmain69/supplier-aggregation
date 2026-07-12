"""Offer database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/offer/alembic.ini upgrade
head`` (or ``make migrate svc=offer``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register the offer tables on Base.metadata before create_all.
from offer.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the offer tables (offer + offer_processed_events)."""
    await create_all(engine)
