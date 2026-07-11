"""Event-consumer entry point (separate process from the API).

Consumes ``supplier.product.discovered`` and upserts supplier products idempotently.
Run with ``python -m catalog.consumer``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer
from sa_persistence.db import create_engine, create_session_factory

from catalog.events.handlers import build_discovered_handler
from catalog.settings import Settings
from sa_contracts import EVENT_REGISTRY

_DISCOVERED = "supplier.product.discovered"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    handler = build_discovered_handler(session_factory)
    consumer = KafkaEventConsumer(
        settings.kafka_bootstrap,
        group_id=settings.consumer_group,
        topics=[EVENT_REGISTRY[_DISCOVERED].topic],
    )
    async with consumer:
        await consumer.consume(handler)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
