"""Transactional outbox store (hard rule 3).

A producer writes its event into the ``outbox`` table **in the same transaction** as the
business change via :func:`enqueue` — no dual write, no lost or phantom events. A relay
later publishes unsent rows (see :mod:`sa_persistence.relay`).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from sa_core.events import OutboxRecord
from sa_core.time import utc_now
from sa_persistence.db import Base


class OutboxRow(Base):
    """A pending (or sent) event in a service's outbox table."""

    __tablename__ = "outbox"

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    topic: Mapped[str] = mapped_column(String(255))
    partition_key: Mapped[str] = mapped_column("key", String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)


def enqueue(session: AsyncSession, record: OutboxRecord) -> OutboxRow:
    """Stage an event row in the caller's transaction. The caller commits."""
    row = OutboxRow(
        id=record.id,
        topic=record.topic,
        partition_key=record.key,
        payload=record.envelope,
    )
    session.add(row)
    return row


async def fetch_unsent(session: AsyncSession, *, limit: int) -> Sequence[OutboxRow]:
    """Return the oldest unsent rows, locking them so concurrent relays don't collide.

    On PostgreSQL this uses ``FOR UPDATE SKIP LOCKED``; other dialects (e.g. SQLite in
    tests) fall back to a plain ordered select.
    """
    stmt = (
        select(OutboxRow)
        .where(OutboxRow.sent_at.is_(None))
        .order_by(OutboxRow.created_at)
        .limit(limit)
    )
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    result = await session.execute(stmt)
    return result.scalars().all()


async def mark_sent(session: AsyncSession, ids: Sequence[str]) -> None:
    """Mark rows as published (sets ``sent_at``)."""
    if not ids:
        return
    await session.execute(update(OutboxRow).where(OutboxRow.id.in_(ids)).values(sent_at=utc_now()))
