"""Event-consumer entry point. Run with ``python -m price_history.consumer``.

Runs two consumers concurrently: ``supplier.offer.price-changed`` (raw supplier prices) and
``offer.effective-price.changed`` (effective UAH prices), each into its own hypertable.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer, KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory

from price_history.events.handlers import (
    build_effective_price_changed_handler,
    build_price_changed_handler,
)
from price_history.settings import Settings
from sa_contracts import EVENT_REGISTRY

_PRICE_CHANGED = "supplier.offer.price-changed"
_EFFECTIVE_CHANGED = "offer.effective-price.changed"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    # Both consumers route poison messages to the same DLQ publisher (ADR-0006).
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="price-history-dlq") as dlq:
        raw = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=settings.consumer_group,
            topics=[EVENT_REGISTRY[_PRICE_CHANGED].topic],
            dlq_sink=dlq,
        )
        effective = KafkaEventConsumer(
            settings.kafka_bootstrap,
            group_id=f"{settings.consumer_group}.effective",
            topics=[EVENT_REGISTRY[_EFFECTIVE_CHANGED].topic],
            dlq_sink=dlq,
        )
        async with raw, effective:
            await asyncio.gather(
                raw.consume(build_price_changed_handler(session_factory)),
                effective.consume(build_effective_price_changed_handler(session_factory)),
            )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
