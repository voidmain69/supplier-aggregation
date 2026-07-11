from __future__ import annotations

import json
from typing import Any

import pytest
from sa_messaging.kafka import KafkaPublisher


class _FakeProducer:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self.sent: list[tuple[str, bytes, bytes | None]] = []

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def send_and_wait(self, topic: str, value: bytes, key: bytes | None = None) -> Any:
        self.sent.append((topic, value, key))


async def test_publish__encodes_payload_json_and_key_bytes() -> None:
    producer = _FakeProducer()
    publisher = KafkaPublisher("localhost:9092", producer_factory=lambda: producer)

    async with publisher:
        await publisher.publish(
            topic="sa.supplier.product",
            key="01J0000000000000000PROD",
            payload={"schema_version": 1, "external_id": "100463720"},
        )

    assert producer.started and producer.stopped
    topic, value, key = producer.sent[0]
    assert topic == "sa.supplier.product"
    assert key == b"01J0000000000000000PROD"
    assert json.loads(value) == {"schema_version": 1, "external_id": "100463720"}


async def test_publish__before_start__raises() -> None:
    publisher = KafkaPublisher("localhost:9092", producer_factory=_FakeProducer)
    with pytest.raises(RuntimeError, match="not started"):
        await publisher.publish(topic="t", key="k", payload={})


async def test_stop__without_start__is_safe() -> None:
    publisher = KafkaPublisher("localhost:9092", producer_factory=_FakeProducer)
    await publisher.stop()  # must not raise
