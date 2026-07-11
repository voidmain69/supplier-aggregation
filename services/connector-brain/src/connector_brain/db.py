"""Service database wiring.

Registers the service's tables on the shared persistence ``Base`` and creates them. Used
by tests and local runs; production schema management via Alembic is a follow-up (the
change is purely additive: the ``outbox`` and ``supplier_product_identity`` tables).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow as _OutboxRow  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for their side effect: registering tables on Base.metadata before create_all.
from connector_brain.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create the service's tables (outbox + supplier_product_identity)."""
    await create_all(engine)
