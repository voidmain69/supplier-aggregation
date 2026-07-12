"""Sync scheduling policy (pure domain — no I/O, no framework).

Decides which accounts are due for a sync given each account's interval and when it last
ran. The orchestrator applies this every tick and emits ``sync.job.requested`` for the due
ones; connectors do the actual fetching.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AccountSchedule:
    """One account and how often it should be synced."""

    account_id: str
    supplier_code: str
    credentials_ref: str | None
    settlement_currency: str
    kind: str  # products | offers | all
    interval_seconds: float


def is_due(schedule: AccountSchedule, last_requested_at: datetime | None, now: datetime) -> bool:
    """True if the account has never run or its interval has elapsed since the last run."""
    if last_requested_at is None:
        return True
    return (now - last_requested_at).total_seconds() >= schedule.interval_seconds


def due_accounts(
    schedules: list[AccountSchedule],
    last_requested: dict[str, datetime],
    now: datetime,
) -> list[AccountSchedule]:
    """The subset of ``schedules`` due to run at ``now``."""
    return [s for s in schedules if is_due(s, last_requested.get(s.account_id), now)]
