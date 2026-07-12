"""Scheduler on Postgres: due accounts -> outbox -> relay. Integration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sync_orchestrator.domain.schedule import AccountSchedule
from sync_orchestrator.scheduler import run_tick

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


async def test_run_tick_on_postgres(
    pg_session_factory: SessionFactory, schedule: AccountSchedule
) -> None:
    now = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)
    assert await run_tick(pg_session_factory, [schedule], now=now) == 1

    publisher = InMemoryPublisher()
    assert await OutboxRelay(pg_session_factory, publisher).drain() == 1
    topic, _key, payload = publisher.published[0]
    assert topic == "sa.sync.job"
    assert payload["data"]["account_id"] == schedule.account_id
