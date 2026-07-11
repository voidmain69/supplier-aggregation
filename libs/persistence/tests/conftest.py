from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from sa_persistence.db import create_all, create_session_factory
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sa_core.events import OutboxRecord


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A fresh in-memory SQLite database per test (StaticPool keeps one shared connection)."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await create_all(engine)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
def make_record() -> Callable[..., OutboxRecord]:
    def _make(record_id: str, *, subject: str = "01J0000000000000000OFFER") -> OutboxRecord:
        envelope: dict[str, Any] = {
            "specversion": "1.0",
            "id": record_id,
            "source": "//sa/connector-brain",
            "type": "supplier.offer.price-changed",
            "time": "2026-07-11T10:00:00Z",
            "subject": subject,
            "dataschema": "https://contracts.sa.internal/events/supplier.offer.price-changed.json",
            "data": {"offer_id": subject, "new_price": "9900.0000"},
        }
        return OutboxRecord.for_event(topic="sa.supplier.offer", envelope=envelope)

    return _make
