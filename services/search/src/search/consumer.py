"""Indexing consumer entry point (separate process from the API).

Runs two consumers concurrently: ``supplier.product.discovered`` (index supplier products) and
``catalog.product.updated`` (index canonical products). Run with ``python -m search.consumer``.
"""

from __future__ import annotations

import asyncio

from sa_messaging import KafkaEventConsumer
from sa_persistence.db import create_engine, create_session_factory

from sa_contracts import EVENT_REGISTRY
from search.adapters.embedder import build_embedder
from search.adapters.sparse_embedder import build_sparse_embedder
from search.events.handlers import build_canonical_updated_handler, build_discovered_handler
from search.settings import Settings

_DISCOVERED = "supplier.product.discovered"
_CATALOG_UPDATED = "catalog.product.updated"


async def run() -> None:
    settings = Settings()
    session_factory = create_session_factory(create_engine(settings.db_dsn))
    embedder = build_embedder(settings.embedder_url)
    sparse_embedder = build_sparse_embedder(settings.sparse_embedder_url)
    discovered = KafkaEventConsumer(
        settings.kafka_bootstrap,
        group_id=settings.consumer_group,
        topics=[EVENT_REGISTRY[_DISCOVERED].topic],
    )
    canonical = KafkaEventConsumer(
        settings.kafka_bootstrap,
        group_id=f"{settings.consumer_group}.canonical",
        topics=[EVENT_REGISTRY[_CATALOG_UPDATED].topic],
    )
    async with discovered, canonical:
        await asyncio.gather(
            discovered.consume(
                build_discovered_handler(
                    session_factory, embedder=embedder, sparse_embedder=sparse_embedder
                )
            ),
            canonical.consume(
                build_canonical_updated_handler(
                    session_factory, embedder=embedder, sparse_embedder=sparse_embedder
                )
            ),
        )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
