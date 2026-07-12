"""Outbox relay process: publishes matching's staged events to Kafka.

Matching both consumes (``supplier.product.discovered`` -> see ``matching.consumer``) and
produces (``matching.link.confirmed`` on auto-link or operator confirmation). This relay
drains the produced side. Run with ``python -m matching.relay``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.relay import OutboxRelay, RelayWorker

from matching.settings import Settings


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="matching-relay") as pub:
        await RelayWorker(OutboxRelay(session_factory, pub)).run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
