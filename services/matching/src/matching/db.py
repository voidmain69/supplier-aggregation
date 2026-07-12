"""Matching database wiring (schema create for tests/local; Alembic is a follow-up)."""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow as _OutboxRow  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register matching + outbox tables on Base.metadata.
from matching.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the matching tables (canonical_product, product_link, outbox, ...)."""
    await create_all(engine)
