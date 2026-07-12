"""pricing engine: supplier_account terms + offer.effective_price_uah

Additive (expand): a new supplier_account table and a nullable effective_price_uah column
with its ranking index. No backfill — offers get an effective price on their next upsert or
when the account's terms are set.

Revision ID: b2f7c1a9d3e4
Revises: 60f2d4a41ead
Create Date: 2026-07-12 18:40:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2f7c1a9d3e4"
down_revision: str | None = "60f2d4a41ead"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "offer", sa.Column("effective_price_uah", sa.Numeric(precision=14, scale=4), nullable=True)
    )
    op.create_index(
        op.f("ix_offer_effective_price_uah"), "offer", ["effective_price_uah"], unique=False
    )
    op.create_table(
        "supplier_account",
        sa.Column("supplier_account_id", sa.String(length=26), nullable=False),
        sa.Column("discount_pct", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("markup_pct", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("fx_rate_to_uah", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("supplier_account_id"),
    )


def downgrade() -> None:
    op.drop_table("supplier_account")
    op.drop_index(op.f("ix_offer_effective_price_uah"), table_name="offer")
    op.drop_column("offer", "effective_price_uah")
