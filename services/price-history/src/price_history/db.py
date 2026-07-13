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

from price_history.adapters.models import (
    EffectivePricePointRow,
    PricePointRow,
    ProcessedEvent,
)

_HYPERTABLES = ("price_point", "effective_price_point")


async def create_schema(engine: AsyncEngine) -> None:
    """Create price-history's own tables; enable the Timescale hypertables when available."""
    await create_all(
        engine,
        tables=[
            PricePointRow.__table__,
            EffectivePricePointRow.__table__,
            ProcessedEvent.__table__,
        ],
    )
    if engine.dialect.name != "postgresql":
        return
    async with engine.begin() as conn:
        available = await conn.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
        )
        if available.first() is None:
            return  # plain Postgres (e.g. tests) — keep them ordinary tables
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        for table in _HYPERTABLES:
            await conn.execute(
                text(
                    f"SELECT create_hypertable('{table}', 'ts', "
                    "if_not_exists => TRUE, migrate_data => TRUE)"
                )
            )
