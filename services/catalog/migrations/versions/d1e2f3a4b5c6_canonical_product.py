"""add catalog_product (catalog owns the canonical card)

Additive migration (expand): the catalog now owns the canonical (platform) product, rebuilt from
its member supplier products on ``matching.link.confirmed`` and emitted as
``catalog.product.updated``. The outbox table already exists (initial schema).

Revision ID: d1e2f3a4b5c6
Revises: 4656245eb33e
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "4656245eb33e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_product",
        sa.Column("canonical_product_id", sa.String(length=26), nullable=False),
        sa.Column("gtin", sa.String(length=14), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("supplier_product_ids", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("canonical_product_id"),
    )
    op.create_index(op.f("ix_catalog_product_gtin"), "catalog_product", ["gtin"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_catalog_product_gtin"), table_name="catalog_product")
    op.drop_table("catalog_product")
