"""Sync-orchestrator database wiring.

``create_schema`` builds the service's own tables (schedule state + outbox) — the fast path
for unit tests and local runs. Production applies the migrations instead: ``alembic -c
services/sync-orchestrator/alembic.ini upgrade head`` (or ``make migrate svc=sync-orchestrator``).
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sa_persistence.outbox import OutboxRow
from sqlalchemy.ext.asyncio import AsyncEngine

from sync_orchestrator.adapters.models import SyncScheduleState


async def create_schema(engine: AsyncEngine) -> None:
    """Create the orchestrator's own tables (sync_schedule_state + outbox)."""
    await create_all(engine, tables=[SyncScheduleState.__table__, OutboxRow.__table__])
