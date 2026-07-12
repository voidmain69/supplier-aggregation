"""Price-history database wiring.

Creates the tables and, when TimescaleDB is available (production), turns ``price_point``
into a hypertable partitioned by ``ts``. On plain Postgres or SQLite (tests) that step is
skipped — the table works identically, just without the time-series optimizations.
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
