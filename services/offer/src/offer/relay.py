"""Outbox relay process: publishes the offer service's staged events to Kafka.

Offer both consumes (``supplier.offer.price-changed`` -> see ``offer.consumer``) and produces
(``offer.effective-price.changed`` when the effective price moves). This relay drains the
produced side from the transactional outbox. Run with ``python -m offer.relay``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.relay import OutboxRelay, RelayWorker

from offer.settings import Settings


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="offer-relay") as pub:
        await RelayWorker(OutboxRelay(session_factory, pub)).run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
