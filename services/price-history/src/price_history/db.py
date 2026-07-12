"""Price-history database wiring.

``create_schema`` builds the tables directly (fast path for unit tests and local runs) and,
when TimescaleDB is available, turns ``price_point`` into a hypertable partitioned by ``ts``.
On plain Postgres or SQLite that step is skipped — the table works identically. Production
applies the migrations instead — ``alembic -c services/price-history/alembic.ini upgrade
head`` (or ``make migrate svc=price-history``) — which carries the same hypertable step.
"""

from __future__ import annotations

from sa_persistence.db import create_all
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Import for side effect: register price-history + outbox tables on Base.metadata.
from price_history.adapters import models as _models  # noqa: F401


async def create_schema(engine: AsyncEngine) -> None:
    """Create tables; enable the Timescale hypertable when the extension is present."""
    await create_all(engine)
    if engine.dialect.name != "postgresql":
        return
    async with engine.begin() as conn:
        available = await conn.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
        )
        if available.first() is None:
            return  # plain Postgres (e.g. tests) — keep it an ordinary table
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        await conn.execute(
            text(
                "SELECT create_hypertable('price_point', 'ts', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            )
        )
