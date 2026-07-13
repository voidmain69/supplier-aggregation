"""Outbox relay process: publishes the catalog's staged events to Kafka.

The catalog consumes (``supplier.product.discovered``, ``matching.link.confirmed``) and now also
produces (``catalog.product.updated`` when a canonical card is rebuilt). This relay drains the
produced side from the outbox. Run with ``python -m catalog.relay``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.relay import OutboxRelay, RelayWorker

from catalog.settings import Settings


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="catalog-relay") as pub:
        await RelayWorker(OutboxRelay(session_factory, pub)).run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
