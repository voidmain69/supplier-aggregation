"""Event-consumer entry point (separate process from the API).

Runs two consumers concurrently: ``supplier.product.discovered`` (upsert products) and
``matching.link.confirmed`` (record the canonical mapping). Run with
``python -m catalog.consumer``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer, KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory

from catalog.events.handlers import build_discovered_handler, build_link_confirmed_handler
from catalog.settings import Settings
from sa_contracts import EVENT_REGISTRY

_DISCOVERED = "supplier.product.discovered"
_LINK_CONFIRMED = "matching.link.confirmed"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))

    async with KafkaPublisher(settings.kafka_bootstrap, client_id="catalog-dlq") as dlq:
        discovered = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=f"{settings.consumer_group}.products",
            topics=[EVENT_REGISTRY[_DISCOVERED].topic],
            dlq_sink=dlq,
        )
        links = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=f"{settings.consumer_group}.links",
            topics=[EVENT_REGISTRY[_LINK_CONFIRMED].topic],
            dlq_sink=dlq,
        )
        async with discovered, links:
            await asyncio.gather(
                discovered.consume(build_discovered_handler(session_factory)),
                links.consume(build_link_confirmed_handler(session_factory)),
            )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
