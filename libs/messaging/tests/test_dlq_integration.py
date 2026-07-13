"""Dead-letter routing on a real Kafka broker. Integration — Docker only.

Publishes an event, makes the handler fail, and asserts the message lands on ``sa.dlq.<topic>``
with the original payload plus the ``x-attempts`` / ``x-original-topic`` bookkeeping headers.
"""

from __future__ import annotations

import asyncio

import pytest
from sa_messaging.consumer import KafkaEventConsumer, dlq_topic_for
from sa_messaging.kafka import KafkaPublisher

pytestmark = pytest.mark.integration

_TOPIC = "sa.supplier.offer"


async def test_failing_handler__routes_message_to_dlq_with_headers() -> None:
    from testcontainers.kafka import KafkaContainer  # noqa: PLC0415

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()

        async with KafkaPublisher(bootstrap) as publisher:
            await publisher.publish(
                topic=_TOPIC,
                key="01J0000000000000000OFFER",
                payload={"id": "01J0000000000000000EVT", "type": "supplier.offer.price-changed"},
            )

        async def always_fails(_: dict[str, object]) -> None:
            raise ValueError("handler exploded")

        async with KafkaPublisher(bootstrap, client_id="offer-dlq") as dlq:
            consumer = KafkaEventConsumer(
                bootstrap,
                group_id="offer.ingest",
                topics=[_TOPIC],
                dlq_sink=dlq,
                retry_backoffs=(),  # no retries: dead-letter after the first failure
            )
            async with consumer:
                await asyncio.wait_for(consumer.consume(always_fails, max_messages=1), timeout=30)

        record = await _read_one(bootstrap, dlq_topic_for(_TOPIC))
        headers = dict(record.headers)
        assert (
            record.value == b'{"id":"01J0000000000000000EVT","type":"supplier.offer.price-changed"}'
        )
        assert headers["x-attempts"] == b"1"
        assert headers["x-original-topic"] == _TOPIC.encode()
        assert b"handler exploded" in headers["x-failure-reason"]


async def _read_one(bootstrap: str, topic: str):  # type: ignore[no-untyped-def]
    from aiokafka import AIOKafkaConsumer  # noqa: PLC0415

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id="dlq-reader",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        return await asyncio.wait_for(consumer.getone(), timeout=30)
    finally:
        await consumer.stop()
