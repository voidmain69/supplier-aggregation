"""add decision_log (curation audit journal)

Additive migration (expand): an append-only audit log of operator curation decisions
(confirm / reject / create-new / merge), ordered by its ULID id. Surfaced via
GET /v1/curation/decisions.

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_log",
        sa.Column("decision_id", sa.String(length=26), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("supplier_product_id", sa.String(length=26), nullable=True),
        sa.Column("canonical_product_id", sa.String(length=26), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("operator", sa.String(length=64), nullable=False),
        sa.Column("note", sa.String(length=512), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index(
        op.f("ix_decision_log_supplier_product_id"),
        "decision_log",
        ["supplier_product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_decision_log_supplier_product_id"), table_name="decision_log")
    op.drop_table("decision_log")
