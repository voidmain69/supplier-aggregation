"""KafkaPublisher against a real broker (testcontainers Kafka). Integration — Docker only."""

from __future__ import annotations

import asyncio
import json

import pytest
from sa_messaging.kafka import KafkaPublisher

pytestmark = pytest.mark.integration


async def test_publish_roundtrip_on_kafka() -> None:
    from aiokafka import AIOKafkaConsumer  # noqa: PLC0415
    from testcontainers.kafka import KafkaContainer  # noqa: PLC0415

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()

        async with KafkaPublisher(bootstrap) as publisher:
            await publisher.publish(
                topic="sa.supplier.product",
                key="01J0000000000000000PROD",
                payload={"schema_version": 1, "external_id": "100463720"},
            )

        consumer = AIOKafkaConsumer(
            "sa.supplier.product",
            bootstrap_servers=bootstrap,
            auto_offset_reset="earliest",
            group_id="itest",
        )
        await consumer.start()
        try:
            message = await asyncio.wait_for(consumer.getone(), timeout=30)
        finally:
            await consumer.stop()

        assert message.key == b"01J0000000000000000PROD"
        assert json.loads(message.value) == {"schema_version": 1, "external_id": "100463720"}
