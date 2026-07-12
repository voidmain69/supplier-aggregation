"""Sync-orchestrator tables (on the shared persistence Base)."""

from __future__ import annotations

from datetime import datetime

from sa_persistence.db import Base
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class SyncScheduleState(Base):
    """When each account was last asked to sync — so restarts don't re-request immediately."""

    __tablename__ = "sync_schedule_state"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
