from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sa_messaging.consumer import KafkaEventConsumer


class _Msg:
    def __init__(self, value: bytes) -> None:
        self.value = value


class _FakeConsumer:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._messages = [_Msg(json.dumps(p).encode()) for p in payloads]
        self.started = False
        self.stopped = False
        self.commits = 0

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def commit(self) -> None:
        self.commits += 1

    async def __aiter__(self) -> AsyncIterator[_Msg]:
        for message in self._messages:
            yield message


async def test_consume__handles_and_commits_each_event() -> None:
    events = [{"id": "01JA", "type": "x"}, {"id": "01JB", "type": "y"}]
    fake = _FakeConsumer(events)
    consumer = KafkaEventConsumer(
        "localhost:9092", group_id="g", topics=["t"], consumer_factory=lambda: fake
    )

    seen: list[dict[str, Any]] = []

    async with consumer:
        processed = await consumer.consume(_collector(seen))

    assert fake.started and fake.stopped
    assert processed == 2
    assert [e["id"] for e in seen] == ["01JA", "01JB"]
    assert fake.commits == 2  # committed after each successful handle


async def test_consume__respects_max_messages() -> None:
    fake = _FakeConsumer([{"id": "1"}, {"id": "2"}, {"id": "3"}])
    consumer = KafkaEventConsumer(
        "localhost:9092", group_id="g", topics=["t"], consumer_factory=lambda: fake
    )

    seen: list[dict[str, Any]] = []
    async with consumer:
        processed = await consumer.consume(_collector(seen), max_messages=1)

    assert processed == 1
    assert len(seen) == 1
    assert fake.commits == 1


async def test_consume__before_start__raises() -> None:
    consumer = KafkaEventConsumer("localhost:9092", group_id="g", topics=["t"])
    with pytest.raises(RuntimeError, match="not started"):
        await consumer.consume(_collector([]))


def _collector(sink: list[dict[str, Any]]) -> Any:
    async def _handle(envelope: dict[str, Any]) -> None:
        sink.append(envelope)

    return _handle
