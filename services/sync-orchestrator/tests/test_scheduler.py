"""Scheduler tick: emits sync.job.requested for due accounts and records state (SQLite)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema.validators import Draft202012Validator
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sync_orchestrator.adapters.repository import load_last_requested
from sync_orchestrator.domain.schedule import AccountSchedule
from sync_orchestrator.scheduler import run_tick

SessionFactory = async_sessionmaker[AsyncSession]

_SCHEMA = json.loads(
    (
        Path(__file__).resolve().parents[3] / "contracts" / "events" / "sync.job.requested.json"
    ).read_text(encoding="utf-8")
)
_NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


async def test_run_tick__emits_and_validates_for_due_account(
    sqlite_session_factory: SessionFactory, schedule: AccountSchedule
) -> None:
    emitted = await run_tick(sqlite_session_factory, [schedule], now=_NOW)
    assert emitted == 1

    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1
    topic, key, payload = publisher.published[0]
    assert topic == "sa.sync.job"
    assert key == schedule.account_id  # keyed by account_id
    Draft202012Validator(_SCHEMA).validate(payload["data"])
    assert payload["data"]["kind"] == "all"
    assert payload["data"]["mode"] == "delta"  # the scheduled cadence carries its mode

    async with sqlite_session_factory() as session:
        assert (await load_last_requested(session))[schedule.account_id] == _NOW


async def test_run_tick__not_due_within_interval_emits_nothing(
    sqlite_session_factory: SessionFactory, schedule: AccountSchedule
) -> None:
    await run_tick(sqlite_session_factory, [schedule], now=_NOW)
    again = await run_tick(sqlite_session_factory, [schedule], now=_NOW + timedelta(minutes=30))
    assert again == 0
    assert await OutboxRelay(sqlite_session_factory, InMemoryPublisher()).drain() == 1  # only once


async def test_run_tick__due_again_after_interval(
    sqlite_session_factory: SessionFactory, schedule: AccountSchedule
) -> None:
    await run_tick(sqlite_session_factory, [schedule], now=_NOW)
    later = await run_tick(sqlite_session_factory, [schedule], now=_NOW + timedelta(hours=2))
    assert later == 1
    assert await OutboxRelay(sqlite_session_factory, InMemoryPublisher()).drain() == 2
