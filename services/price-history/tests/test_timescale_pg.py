"""price_daily continuous aggregate on a real TimescaleDB (testcontainers). Integration only.

Runs the price-history Alembic migrations against Timescale and asserts the ``price_daily``
continuous aggregate is created, refreshes, and returns the daily rollup — the production path
the portable SQLite query stands in for.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]


def _asyncpg(url: str) -> str:
    return re.sub(r"^postgresql\+?\w*", "postgresql+asyncpg", url)


async def _seed_and_read(dsn: str) -> list[tuple]:
    engine = create_async_engine(dsn)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO price_point "
                    "(offer_id, ts, supplier_account_id, supplier_product_id, price, currency, "
                    " price_uah) VALUES "
                    "('o1', '2026-07-11 10:00+00', 'a1', 'p1', 1, 'USD', 9900), "
                    "('o1', '2026-07-11 12:00+00', 'a1', 'p1', 1, 'USD', 9500)"
                )
            )
        # Continuous aggregates refresh out of band; force it so the view has data to read.
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("CALL refresh_continuous_aggregate('price_daily', NULL, NULL)"))
            rows = (
                await conn.execute(
                    text("SELECT min_uah, max_uah, last_uah FROM price_daily WHERE offer_id = 'o1'")
                )
            ).all()
            return list(rows)
    finally:
        await engine.dispose()


def test_price_daily_cagg__is_created_and_rolls_up() -> None:
    from alembic import command  # noqa: PLC0415
    from alembic.config import Config  # noqa: PLC0415
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer("timescale/timescaledb:2.17.2-pg16") as pg:
        dsn = _asyncpg(pg.get_connection_url())
        os.environ["PRICE_HISTORY_DB_DSN"] = dsn
        try:
            config = Config(str(ROOT / "services" / "price-history" / "alembic.ini"))
            command.upgrade(config, "head")

            rows = asyncio.run(_seed_and_read(dsn))
            assert rows == [(9500, 9900, 9500)]  # min, max, last for the day

            command.downgrade(config, "base")
        finally:
            os.environ.pop("PRICE_HISTORY_DB_DSN", None)
