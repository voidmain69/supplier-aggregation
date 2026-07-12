"""Event-consumer entry point (separate process from the API).

Consumes ``supplier.product.discovered`` and auto-links by GTIN, emitting
``matching.link.confirmed`` via the outbox. Run with ``python -m matching.consumer``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer, KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory

from matching.events.handlers import build_discovered_handler
from matching.settings import Settings
from sa_contracts import EVENT_REGISTRY

_DISCOVERED = "supplier.product.discovered"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    handler = build_discovered_handler(session_factory)
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="matching-dlq") as dlq:
        consumer = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=settings.consumer_group,
            topics=[EVENT_REGISTRY[_DISCOVERED].topic],
            dlq_sink=dlq,
        )
        async with consumer:
            await consumer.consume(handler)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
