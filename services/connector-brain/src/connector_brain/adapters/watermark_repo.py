"""Read/advance the per-account sync watermark (the delta-sync baseline)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from connector_brain.adapters.models import SyncWatermark
from sa_core.time import ensure_utc, utc_now


def _as_utc(value: datetime) -> datetime:
    """Read a stored UTC timestamp as tz-aware (SQLite drops the tz on round-trip)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


async def get_watermark(
    session: AsyncSession, *, supplier_code: str, account_id: str
) -> datetime | None:
    """The account's last successful sync time, or None if it has never synced."""
    row = await session.get(SyncWatermark, (supplier_code, account_id))
    return _as_utc(row.last_synced_at) if row is not None else None


async def set_watermark(
    session: AsyncSession, *, supplier_code: str, account_id: str, synced_at: datetime
) -> None:
    """Advance the account's watermark to ``synced_at`` (upsert)."""
    synced_at = ensure_utc(synced_at)
    row = await session.get(SyncWatermark, (supplier_code, account_id))
    if row is None:
        session.add(
            SyncWatermark(
                supplier_code=supplier_code, account_id=account_id, last_synced_at=synced_at
            )
        )
        return
    row.last_synced_at = synced_at
    row.updated_at = utc_now()
