"""price_daily continuous aggregate + compression policy

Timescale-only (guarded): materialize a daily UAH-price rollup (min/max/avg/last per offer) as a
continuous aggregate with an hourly refresh policy, and compress raw price_point chunks older
than 90 days. On plain Postgres / SQLite (tests) the whole migration is a no-op — the daily API
query works portably against the raw table either way.

Creating a continuous aggregate cannot run inside a transaction, so it is done in an
``autocommit_block``.

Revision ID: d7f3b1e9a842
Revises: f59bc0958fe5
Create Date: 2026-07-12 20:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7f3b1e9a842"
down_revision: str | None = "f59bc0958fe5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CREATE_CAGG = """
CREATE MATERIALIZED VIEW price_daily
WITH (timescaledb.continuous) AS
SELECT offer_id,
       time_bucket('1 day', ts) AS day,
       count(*)          AS cnt,
       min(price_uah)    AS min_uah,
       max(price_uah)    AS max_uah,
       avg(price_uah)    AS avg_uah,
       last(price_uah, ts) AS last_uah
FROM price_point
GROUP BY offer_id, day
WITH NO DATA
"""


def _timescale_installed(bind: sa.engine.Connection) -> bool:
    if bind.dialect.name != "postgresql":
        return False
    return (
        bind.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")).first()
        is not None
    )


def upgrade() -> None:
    bind = op.get_bind()
    if not _timescale_installed(bind):
        return  # plain Postgres / SQLite — the daily API query runs against the raw table
    with op.get_context().autocommit_block():
        op.execute(_CREATE_CAGG)
    op.execute(
        "SELECT add_continuous_aggregate_policy('price_daily', "
        "start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour', "
        "schedule_interval => INTERVAL '1 hour')"
    )
    op.execute(
        "ALTER TABLE price_point SET ("
        "timescaledb.compress, "
        "timescaledb.compress_segmentby = 'offer_id', "
        "timescaledb.compress_orderby = 'ts DESC')"
    )
    op.execute("SELECT add_compression_policy('price_point', INTERVAL '90 days')")


def downgrade() -> None:
    bind = op.get_bind()
    if not _timescale_installed(bind):
        return
    op.execute("SELECT remove_compression_policy('price_point', if_exists => true)")
    op.execute("ALTER TABLE price_point SET (timescaledb.compress = false)")
    with op.get_context().autocommit_block():
        op.execute("DROP MATERIALIZED VIEW IF EXISTS price_daily")
