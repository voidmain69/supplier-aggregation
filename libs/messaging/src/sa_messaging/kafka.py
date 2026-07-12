"""Kafka publisher — the concrete broker adapter behind the outbox relay.

Structurally satisfies ``sa_persistence.relay.Publisher`` (topic/key/payload), so a relay
ships outbox rows to Kafka. Payloads are JSON-encoded; the aggregate key becomes the
partition key so all events for one aggregate keep their order. ``acks=all`` by default.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, Protocol, cast

from aiokafka import AIOKafkaProducer


class _Producer(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def send_and_wait(
        self,
        topic: str,
        value: bytes,
        key: bytes | None = ...,
        headers: list[tuple[str, bytes]] | None = ...,
    ) -> Any: ...


ProducerFactory = Callable[[], _Producer]


def _encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class KafkaPublisher:
    """Publishes events to Kafka. Manage its lifecycle with ``async with`` or start/stop."""

    def __init__(
        self,
        bootstrap_servers: str,
        *,
        acks: str = "all",
        client_id: str = "sa-producer",
        producer_factory: ProducerFactory | None = None,
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._acks = acks
        self._client_id = client_id
        self._factory = producer_factory
        self._producer: _Producer | None = None

    def _build(self) -> _Producer:
        if self._factory is not None:
            return self._factory()
        producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap, acks=self._acks, client_id=self._client_id
        )
        return cast(_Producer, producer)

    async def start(self) -> None:
        self._producer = self._build()
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, *, topic: str, key: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("KafkaPublisher not started; use `async with` or call start()")
        await self._producer.send_and_wait(topic, value=_encode(payload), key=key.encode("utf-8"))

    async def send_raw(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: list[tuple[str, bytes]],
    ) -> None:
        """Publish an already-encoded message verbatim (used to dead-letter a failed event)."""
        if self._producer is None:
            raise RuntimeError("KafkaPublisher not started; use `async with` or call start()")
        await self._producer.send_and_wait(topic, value=value, key=key, headers=headers)

    async def __aenter__(self) -> KafkaPublisher:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()
