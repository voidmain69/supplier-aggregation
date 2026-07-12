from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sa_messaging.consumer import KafkaEventConsumer, dlq_topic_for


class _Msg:
    def __init__(
        self,
        value: bytes,
        *,
        topic: str = "sa.supplier.offer",
        key: bytes | None = b"agg-1",
        headers: list[tuple[str, bytes]] | None = None,
    ) -> None:
        self.value = value
        self.topic = topic
        self.key = key
        self.headers = headers or [("ce-id", b"01JA")]


class _RecordingSink:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_raw(
        self, *, topic: str, key: bytes | None, value: bytes, headers: list[tuple[str, bytes]]
    ) -> None:
        self.sent.append({"topic": topic, "key": key, "value": value, "headers": headers})


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


async def test_dispatch__handler_recovers_before_retries_exhausted__commits_no_dlq() -> None:
    fake = _FakeConsumer([{"id": "1"}])
    sink = _RecordingSink()
    calls = {"n": 0}

    async def flaky(_: dict[str, Any]) -> None:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("transient")

    consumer = KafkaEventConsumer(
        "localhost:9092",
        group_id="g",
        topics=["t"],
        consumer_factory=lambda: fake,
        dlq_sink=sink,
        retry_backoffs=(0.0, 0.0),
        sleep=_no_sleep,
    )
    async with consumer:
        await consumer.consume(flaky)

    assert calls["n"] == 2  # failed once, succeeded on retry
    assert sink.sent == []  # never dead-lettered
    assert fake.commits == 1


async def test_dispatch__retries_exhausted__routes_to_dlq_and_commits() -> None:
    fake = _FakeConsumer([{"id": "1"}])
    sink = _RecordingSink()

    async def always_fails(_: dict[str, Any]) -> None:
        raise ValueError("boom")

    consumer = KafkaEventConsumer(
        "localhost:9092",
        group_id="g",
        topics=["t"],
        consumer_factory=lambda: fake,
        dlq_sink=sink,
        retry_backoffs=(0.0, 0.0),  # 1 initial + 2 retries = 3 attempts
        sleep=_no_sleep,
    )
    async with consumer:
        processed = await consumer.consume(always_fails)

    assert processed == 1
    assert fake.commits == 1  # committed so the poison message cannot wedge the partition
    assert len(sink.sent) == 1
    dead = sink.sent[0]
    assert dead["topic"] == dlq_topic_for("sa.supplier.offer")
    assert dead["key"] == b"agg-1"
    assert dead["value"] == json.dumps({"id": "1"}).encode()
    header = dict(dead["headers"])
    assert header["ce-id"] == b"01JA"  # original headers preserved
    assert header["x-attempts"] == b"3"
    assert header["x-original-topic"] == b"sa.supplier.offer"
    assert b"boom" in header["x-failure-reason"]


async def test_dispatch__no_dlq_sink__reraises_after_retries() -> None:
    fake = _FakeConsumer([{"id": "1"}])

    async def always_fails(_: dict[str, Any]) -> None:
        raise ValueError("boom")

    consumer = KafkaEventConsumer(
        "localhost:9092",
        group_id="g",
        topics=["t"],
        consumer_factory=lambda: fake,
        retry_backoffs=(0.0,),
        sleep=_no_sleep,
    )
    async with consumer:
        with pytest.raises(ValueError, match="boom"):
            await consumer.consume(always_fails)

    assert fake.commits == 0  # not committed: fail-loud so the partition stalls for a human


async def test_dispatch__applies_backoff_between_retries() -> None:
    fake = _FakeConsumer([{"id": "1"}])
    sink = _RecordingSink()
    slept: list[float] = []

    async def record_sleep(delay: float) -> None:
        slept.append(delay)

    async def always_fails(_: dict[str, Any]) -> None:
        raise ValueError("boom")

    consumer = KafkaEventConsumer(
        "localhost:9092",
        group_id="g",
        topics=["t"],
        consumer_factory=lambda: fake,
        dlq_sink=sink,
        retry_backoffs=(1.0, 10.0, 60.0),
        sleep=record_sleep,
    )
    async with consumer:
        await consumer.consume(always_fails)

    assert slept == [1.0, 10.0, 60.0]  # backoff before each of the three retries


def _collector(sink: list[dict[str, Any]]) -> Any:
    async def _handle(envelope: dict[str, Any]) -> None:
        sink.append(envelope)

    return _handle


async def _no_sleep(_: float) -> None:
    return None
