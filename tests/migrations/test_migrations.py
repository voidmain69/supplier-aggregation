"""Every service's Alembic migrations run on Postgres and are reversible.

Lives outside ``services/`` because it drives all services' migration lineages. Sync (not
async) on purpose: ``alembic.command`` runs each service's ``env.py``, which itself calls
``asyncio.run`` — so the test must not already be inside an event loop.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ServiceMigrations:
    name: str  # directory under services/
    env_var: str  # settings DSN env var (env_prefix + _DB_DSN)
    database: str  # database created for this service in the shared container
    tables: set[str] = field(default_factory=set)  # tables the migration must create


SERVICES = [
    ServiceMigrations(
        "connector-brain",
        "CONNECTOR_BRAIN_DB_DSN",
        "brain",
        {"outbox", "supplier_product_identity", "offer_identity"},
    ),
    ServiceMigrations(
        "catalog",
        "CATALOG_DB_DSN",
        "catalog",
        {"supplier_product", "product_canonical_link", "processed_events"},
    ),
    ServiceMigrations(
        "offer", "OFFER_DB_DSN", "offer", {"offer", "supplier_account", "offer_processed_events"}
    ),
    ServiceMigrations(
        "matching",
        "MATCHING_DB_DSN",
        "matching",
        {"canonical_product", "product_link", "matching_processed_events", "outbox"},
    ),
    ServiceMigrations(
        "price-history",
        "PRICE_HISTORY_DB_DSN",
        "pricehistory",
        {"price_point", "effective_price_point", "price_history_processed_events"},
    ),
    ServiceMigrations(
        "sync-orchestrator",
        "SYNC_ORCHESTRATOR_DB_DSN",
        "syncorch",
        {"sync_schedule_state", "outbox"},
    ),
]


def _asyncpg(url: str) -> str:
    return re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", url)


def _dsn_for(base_url: str, database: str) -> str:
    head, _, _old = base_url.rpartition("/")
    return f"{head}/{database}"


async def _create_database(base_dsn: str, database: str) -> None:
    admin = create_async_engine(base_dsn, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        await admin.dispose()


async def _table_names(dsn: str) -> set[str]:
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            return await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
    finally:
        await engine.dispose()


def test_every_service_migration_upgrades_and_downgrades() -> None:
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    # pgvector image so matching's embedding migration (CREATE EXTENSION vector) runs;
    # price-history's Timescale step is guarded and simply skips when the extension is absent.
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        base = _asyncpg(postgres.get_connection_url())
        for svc in SERVICES:
            asyncio.run(_create_database(base, svc.database))
            dsn = _dsn_for(base, svc.database)
            os.environ[svc.env_var] = dsn
            try:
                config = Config(str(ROOT / "services" / svc.name / "alembic.ini"))

                command.upgrade(config, "head")
                after_upgrade = asyncio.run(_table_names(dsn))
                assert svc.tables <= after_upgrade, (svc.name, sorted(after_upgrade))

                command.downgrade(config, "base")
                after_downgrade = asyncio.run(_table_names(dsn))
                assert not (svc.tables & after_downgrade), (svc.name, sorted(after_downgrade))
            finally:
                os.environ.pop(svc.env_var, None)
