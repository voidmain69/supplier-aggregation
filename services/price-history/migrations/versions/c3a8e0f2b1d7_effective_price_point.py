"""effective_price_point: effective UAH price time series

Additive (expand): a second hypertable fed by offer.effective-price.changed, kept separate
from price_point so the raw and effective series never collide on (offer_id, ts).

Revision ID: c3a8e0f2b1d7
Revises: f59bc0958fe5
Create Date: 2026-07-12 18:55:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a8e0f2b1d7"
down_revision: str | None = "d7f3b1e9a842"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "effective_price_point",
        sa.Column("offer_id", sa.String(length=26), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_account_id", sa.String(length=26), nullable=False),
        sa.Column("supplier_product_id", sa.String(length=26), nullable=False),
        sa.Column("effective_price_uah", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("base_price", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("cause", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("offer_id", "ts"),
    )
    op.create_index(
        op.f("ix_effective_price_point_supplier_product_id"),
        "effective_price_point",
        ["supplier_product_id"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        available = bind.execute(
            sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'")
        ).first()
        if available is not None:
            op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
            op.execute(
                "SELECT create_hypertable('effective_price_point', 'ts', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_effective_price_point_supplier_product_id"),
        table_name="effective_price_point",
    )
    op.drop_table("effective_price_point")
