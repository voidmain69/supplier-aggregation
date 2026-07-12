"""Schedule tick loop: emit ``sync.job.requested`` for due accounts via the outbox.

Run with ``python -m sync_orchestrator.scheduler``. Each tick, in one transaction, it finds
accounts whose interval has elapsed, stages a ``sync.job.requested`` for each and records the
request time. The outbox relay ships them to Kafka; the supplier connector acts on them.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_core.ids import new_ulid
from sa_core.time import utc_now
from sync_orchestrator.adapters.repository import load_last_requested, mark_requested
from sync_orchestrator.domain.schedule import AccountSchedule, due_accounts
from sync_orchestrator.events.mapping import sync_requested_record
from sync_orchestrator.settings import Settings


async def run_tick(
    session_factory: async_sessionmaker[AsyncSession],
    schedules: list[AccountSchedule],
    *,
    now: datetime,
) -> int:
    """Emit ``sync.job.requested`` for accounts due at ``now``; return how many. One txn."""
    async with session_factory() as session, session.begin():
        last = await load_last_requested(session)
        due = due_accounts(schedules, last, now)
        for schedule in due:
            enqueue(
                session,
                sync_requested_record(schedule, sync_job_id=new_ulid(), requested_at=now),
            )
            await mark_requested(session, schedule.account_id, now)
        return len(due)


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    schedules = settings.schedules()
    while True:
        await run_tick(session_factory, schedules, now=utc_now())
        await asyncio.sleep(settings.poll_interval_seconds)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
