"""Indexing consumer entry point (separate process from the API).

Consumes ``supplier.product.discovered`` and indexes each product for lexical search.
Run with ``python -m search.consumer``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer
from sa_persistence.db import create_engine, create_session_factory

from sa_contracts import EVENT_REGISTRY
from search.events.handlers import build_discovered_handler
from search.settings import Settings

_DISCOVERED = "supplier.product.discovered"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    consumer = KafkaEventConsumer(
        settings.kafka_bootstrap,
        group_id=settings.consumer_group,
        topics=[EVENT_REGISTRY[_DISCOVERED].topic],
    )
    async with consumer:
        await consumer.consume(build_discovered_handler(session_factory))


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
