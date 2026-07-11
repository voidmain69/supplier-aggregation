"""Outbox relay: publish staged events to the broker, then mark them sent.

Runs as a background loop in each producing service. Each drain locks a batch of unsent
rows (SKIP LOCKED), publishes them, and marks them sent in one transaction. Semantics are
**at-least-once**: if publish succeeds but the commit fails, the row re-publishes next
round — consumers must be idempotent (hard rule 3).
"""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_persistence.outbox import fetch_unsent, mark_sent


class Publisher(Protocol):
    """Publishes one event to the broker (e.g. a Kafka producer)."""

    async def publish(self, *, topic: str, key: str, payload: dict[str, Any]) -> None: ...


class InMemoryPublisher:
    """A :class:`Publisher` that records published events — for tests and local runs."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict[str, Any]]] = []

    async def publish(self, *, topic: str, key: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, key, payload))


class OutboxRelay:
    """Drains the outbox to a :class:`Publisher`."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: Publisher,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher

    async def drain(self, *, batch_size: int = 100) -> int:
        """Publish up to ``batch_size`` unsent events; return how many were published."""
        async with self._session_factory() as session, session.begin():
            rows = await fetch_unsent(session, limit=batch_size)
            for row in rows:
                await self._publisher.publish(
                    topic=row.topic, key=row.partition_key, payload=row.payload
                )
            await mark_sent(session, [row.id for row in rows])
            return len(rows)
