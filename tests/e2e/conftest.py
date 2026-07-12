"""Fixtures for the end-to-end pipeline test.

One Postgres container (a separate database per service — nobody shares another service's
schema, hard rule 1) and one Kafka container, both session-scoped because they are slow to
start. All async wiring happens inside the test against these containers.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import pytest


def _asyncpg(url: str) -> str:
    """Rewrite a testcontainers connection URL to the asyncpg driver."""
    return re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", url)


@pytest.fixture(scope="session")
def pg_base_dsn() -> Iterator[str]:
    """Session-wide Postgres; yields the asyncpg DSN of its default database."""
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    # pgvector image: the matching service's schema needs the `vector` extension.
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield _asyncpg(postgres.get_connection_url())


@pytest.fixture(scope="session")
def kafka_bootstrap() -> Iterator[str]:
    """Session-wide Kafka; yields its bootstrap server."""
    from testcontainers.kafka import KafkaContainer  # noqa: PLC0415

    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()
