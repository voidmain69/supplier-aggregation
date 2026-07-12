"""Outbox relay process: publishes connector-brain's staged events to Kafka.

Separate process from the sync jobs and the API. Run with ``python -m connector_brain.relay``.
Drains the ``outbox`` table (discovered / price-changed events) to the broker at-least-once;
consumers are idempotent (hard rule 3).
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaPublisher
from sa_persistence.db import create_engine, create_session_factory
from sa_persistence.relay import OutboxRelay, RelayWorker

from connector_brain.settings import Settings


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    async with KafkaPublisher(settings.kafka_bootstrap, client_id="connector-brain-relay") as pub:
        await RelayWorker(OutboxRelay(session_factory, pub)).run()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
