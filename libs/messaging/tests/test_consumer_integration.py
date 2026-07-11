"""Publisher -> consumer roundtrip on a real Kafka broker. Integration — Docker only."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sa_messaging.consumer import KafkaEventConsumer
from sa_messaging.kafka import KafkaPublisher

pytestmark = pytest.mark.integration


async def test_publish_then_consume_roundtrip() -> None:
    from testcontainers.kafka import KafkaContainer  # noqa: PLC0415

    with KafkaContainer() as kafka:
        bootstrap = kafka.get_bootstrap_server()

        async with KafkaPublisher(bootstrap) as publisher:
            await publisher.publish(
                topic="sa.supplier.product",
                key="01J0000000000000000PROD",
                payload={"id": "01J0000000000000000EVT", "type": "supplier.product.discovered"},
            )

        received: list[dict[str, Any]] = []
        consumer = KafkaEventConsumer(
            bootstrap, group_id="catalog.ingest", topics=["sa.supplier.product"]
        )
        async with consumer:

            async def _handle(envelope: dict[str, Any]) -> None:
                received.append(envelope)

            await asyncio.wait_for(consumer.consume(_handle, max_messages=1), timeout=30)

        assert received == [{"id": "01J0000000000000000EVT", "type": "supplier.product.discovered"}]
