"""Service database wiring.

Registers the service's tables on the shared persistence ``Base``. ``create_schema`` builds
them directly — the fast path for unit tests and local runs. Production applies the
migrations instead: ``alembic -c services/connector-brain/alembic.ini upgrade head`` (or
``make migrate svc=connector-brain``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow
from sqlalchemy.ext.asyncio import AsyncEngine

from connector_brain.adapters.models import OfferIdentity, SupplierProductIdentity


async def create_schema(engine: AsyncEngine) -> None:
    """Create the service's own tables (identity/offer state + outbox)."""
    await create_all(
        engine,
        tables=[
            SupplierProductIdentity.__table__,
            OfferIdentity.__table__,
            OutboxRow.__table__,
        ],
    )
