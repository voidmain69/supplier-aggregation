"""Kafka event consumer — drives an async handler over decoded CloudEvent envelopes.

Manual offset commit *after* the handler succeeds gives at-least-once delivery, so handlers
must be idempotent (hard rule 3). The underlying consumer is injectable, so the loop is
unit-testable without a broker.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Protocol, cast

from aiokafka import AIOKafkaConsumer

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class _Message(Protocol):
    @property
    def value(self) -> bytes: ...


class _Consumer(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def commit(self) -> None: ...
    def __aiter__(self) -> AsyncIterator[_Message]: ...


ConsumerFactory = Callable[[], _Consumer]


class KafkaEventConsumer:
    """Subscribes to topics and runs a handler over each event, committing on success."""

    def __init__(
        self,
        bootstrap_servers: str,
        *,
        group_id: str,
        topics: list[str],
        consumer_factory: ConsumerFactory | None = None,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._factory = consumer_factory
        self._consumer: _Consumer | None = None

    def _build(self) -> _Consumer:
        if self._factory is not None:
            return self._factory()
        consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap,
            group_id=self._group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        return cast(_Consumer, consumer)

    async def start(self) -> None:
        self._consumer = self._build()
        await self._consumer.start()

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def consume(self, handler: EventHandler, *, max_messages: int | None = None) -> int:
        """Run the handler over incoming events; commit each after success. Returns count.

        ``max_messages`` stops the loop after N events (used by tests); omit it in the
        service for an unbounded loop.
        """
        if self._consumer is None:
            raise RuntimeError("KafkaEventConsumer not started; use `async with` or call start()")
        processed = 0
        async for message in self._consumer:
            await handler(json.loads(message.value))
            await self._consumer.commit()
            processed += 1
            if max_messages is not None and processed >= max_messages:
                break
        return processed

    async def __aenter__(self) -> KafkaEventConsumer:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()
