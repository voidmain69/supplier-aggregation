"""sync_watermark: per-account delta-sync baseline

Additive (expand): a new table holding each account's last successful sync time. No backfill —
an account with no watermark falls back to a full sync (which then sets it).

Revision ID: d4e1a7b9c2f0
Revises: 3a9469460280
Create Date: 2026-07-12 19:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e1a7b9c2f0"
down_revision: str | None = "3a9469460280"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_watermark",
        sa.Column("supplier_code", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=26), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("supplier_code", "account_id"),
    )


def downgrade() -> None:
    op.drop_table("sync_watermark")
