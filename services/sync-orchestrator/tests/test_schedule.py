"""Scheduling policy (pure, no DB)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sync_orchestrator.domain.schedule import AccountSchedule, due_accounts, is_due

_NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def _sched(account_id: str, interval: float) -> AccountSchedule:
    return AccountSchedule(
        account_id=account_id,
        supplier_code="brain",
        credentials_ref=None,
        settlement_currency="USD",
        kind="all",
        interval_seconds=interval,
    )


def test_is_due__never_run_is_due() -> None:
    assert is_due(_sched("a", 3600), None, _NOW) is True


def test_is_due__interval_not_elapsed() -> None:
    last = _NOW - timedelta(minutes=30)
    assert is_due(_sched("a", 3600), last, _NOW) is False


def test_is_due__interval_elapsed() -> None:
    last = _NOW - timedelta(hours=2)
    assert is_due(_sched("a", 3600), last, _NOW) is True


def test_due_accounts__filters_to_the_due_ones() -> None:
    schedules = [_sched("a", 3600), _sched("b", 3600), _sched("c", 3600)]
    last = {
        "a": _NOW - timedelta(minutes=10),  # not due
        "b": _NOW - timedelta(hours=3),  # due
        # c never ran -> due
    }
    due = {s.account_id for s in due_accounts(schedules, last, _NOW)}
    assert due == {"b", "c"}
