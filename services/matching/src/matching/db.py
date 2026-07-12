"""Matching database wiring.

``create_schema`` builds the tables directly — the fast path for unit tests and local runs.
Production applies the migrations instead: ``alembic -c services/matching/alembic.ini upgrade
head`` (or ``make migrate svc=matching``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow as _OutboxRow  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register matching + outbox tables on Base.metadata.
from matching.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the matching tables (canonical_product, product_link, outbox, ...)."""
    await create_all(engine)
