"""Kafka event consumer — drives an async handler over decoded CloudEvent envelopes.

Manual offset commit *after* the handler succeeds gives at-least-once delivery, so handlers
must be idempotent (hard rule 3). A failing handler is retried with backoff; once the retries
are exhausted the message is routed to the dead-letter topic ``sa.dlq.<topic>`` (preserving the
original payload + headers, plus ``x-failure-reason``/``x-attempts``) and the offset is
committed so one poison message cannot wedge the partition. Without a dead-letter sink the
error propagates instead, matching the fail-loud default. The underlying consumer is
injectable, so the loop is unit-testable without a broker.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any, Protocol, cast

import structlog
from aiokafka import AIOKafkaConsumer

log = structlog.get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]
Sleep = Callable[[float], Awaitable[None]]

DLQ_TOPIC_PREFIX = "sa.dlq."
# Backoff before each retry (events.md §4): three retries at 1s / 10s / 60s, then dead-letter.
DEFAULT_RETRY_BACKOFFS: tuple[float, ...] = (1.0, 10.0, 60.0)

_FAILURE_REASON_HEADER = "x-failure-reason"
_ATTEMPTS_HEADER = "x-attempts"
_ORIGINAL_TOPIC_HEADER = "x-original-topic"
_DLQ_HEADERS = frozenset({_FAILURE_REASON_HEADER, _ATTEMPTS_HEADER, _ORIGINAL_TOPIC_HEADER})
_MAX_REASON_BYTES = 1024


def dlq_topic_for(topic: str) -> str:
    """Return the dead-letter topic for a source topic: ``sa.dlq.<topic>``."""
    return f"{DLQ_TOPIC_PREFIX}{topic}"


class _Message(Protocol):
    @property
    def value(self) -> bytes: ...
    @property
    def topic(self) -> str: ...
    @property
    def key(self) -> bytes | None: ...
    @property
    def headers(self) -> Sequence[tuple[str, bytes]]: ...


class _Consumer(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def commit(self) -> None: ...
    def __aiter__(self) -> AsyncIterator[_Message]: ...


class DeadLetterSink(Protocol):
    """Ships a failed message verbatim to its dead-letter topic (satisfied by KafkaPublisher)."""

    async def send_raw(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: list[tuple[str, bytes]],
    ) -> None: ...


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
        dlq_sink: DeadLetterSink | None = None,
        retry_backoffs: Sequence[float] = DEFAULT_RETRY_BACKOFFS,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._factory = consumer_factory
        self._dlq_sink = dlq_sink
        self._retry_backoffs = tuple(retry_backoffs)
        self._sleep = sleep
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
            await self._dispatch(handler, message)
            await self._consumer.commit()
            processed += 1
            if max_messages is not None and processed >= max_messages:
                break
        return processed

    async def _dispatch(self, handler: EventHandler, message: _Message) -> None:
        """Handle one message with bounded retries; dead-letter (or re-raise) on exhaustion."""
        event = json.loads(message.value)
        last_exc: Exception | None = None
        for attempt, delay in enumerate((0.0, *self._retry_backoffs), start=1):
            if delay:
                await self._sleep(delay)
            try:
                await handler(event)
                return
            except Exception as exc:
                last_exc = exc
                log.warning(
                    "event_handler_failed", topic=message.topic, attempt=attempt, error=str(exc)
                )
        assert last_exc is not None  # noqa: S101 -- loop body runs >=1 time, so this is set
        if self._dlq_sink is None:
            raise last_exc
        await self._dead_letter(message, last_exc, attempts=len(self._retry_backoffs) + 1)

    async def _dead_letter(self, message: _Message, exc: Exception, *, attempts: int) -> None:
        assert self._dlq_sink is not None  # noqa: S101 -- guarded by caller
        reason = str(exc).encode("utf-8")[:_MAX_REASON_BYTES]
        headers = [(k, v) for k, v in message.headers if k not in _DLQ_HEADERS]
        headers.extend(
            [
                (_FAILURE_REASON_HEADER, reason),
                (_ATTEMPTS_HEADER, str(attempts).encode("utf-8")),
                (_ORIGINAL_TOPIC_HEADER, message.topic.encode("utf-8")),
            ]
        )
        await self._dlq_sink.send_raw(
            topic=dlq_topic_for(message.topic),
            key=message.key,
            value=message.value,
            headers=headers,
        )
        log.error("event_dead_lettered", topic=message.topic, attempts=attempts, error=str(exc))

    async def __aenter__(self) -> KafkaEventConsumer:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()
