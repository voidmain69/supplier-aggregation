"""Event-consumer entry point. Run with ``python -m price_history.consumer``."""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer, KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory

from price_history.events.handlers import build_price_changed_handler
from price_history.settings import Settings
from sa_contracts import EVENT_REGISTRY

_PRICE_CHANGED = "supplier.offer.price-changed"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    handler = build_price_changed_handler(session_factory)
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="price-history-dlq") as dlq:
        consumer = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=settings.consumer_group,
            topics=[EVENT_REGISTRY[_PRICE_CHANGED].topic],
            dlq_sink=dlq,
        )
        async with consumer:
            await consumer.consume(handler)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
