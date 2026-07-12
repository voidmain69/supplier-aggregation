"""Data access for the sync schedule state."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sync_orchestrator.adapters.models import SyncScheduleState


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive timestamps; treat them as UTC so scheduling math stays tz-safe."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


async def load_last_requested(session: AsyncSession) -> dict[str, datetime]:
    """Map account_id -> when it was last requested (missing accounts are absent)."""
    rows = (await session.execute(select(SyncScheduleState))).scalars().all()
    return {row.account_id: _aware(row.last_requested_at) for row in rows}


async def mark_requested(session: AsyncSession, account_id: str, at: datetime) -> None:
    """Record that ``account_id`` was requested at ``at`` (upsert)."""
    existing = await session.get(SyncScheduleState, account_id)
    if existing is None:
        session.add(SyncScheduleState(account_id=account_id, last_requested_at=at))
    else:
        existing.last_requested_at = at
