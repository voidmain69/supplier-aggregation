"""initial schema

Creates the search index tables. On PostgreSQL it also installs pg_trgm + a GIN trigram
index on ``search_text`` so lexical LIKE queries stay fast; on SQLite (tests) that step is a
no-op and the table works identically.

Revision ID: a1c4e8b06f92
Revises:
Create Date: 2026-07-12 19:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e8b06f92"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_document",
        sa.Column("supplier_product_id", sa.String(length=26), nullable=False),
        sa.Column("supplier_code", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("external_code", sa.String(length=128), nullable=True),
        sa.Column("articul", sa.String(length=256), nullable=True),
        sa.Column("gtin", sa.String(length=14), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("brand", sa.String(length=256), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("supplier_product_id"),
    )
    op.create_index(op.f("ix_search_document_supplier_code"), "search_document", ["supplier_code"])
    op.create_index(op.f("ix_search_document_external_code"), "search_document", ["external_code"])
    op.create_index(op.f("ix_search_document_articul"), "search_document", ["articul"])
    op.create_index(op.f("ix_search_document_gtin"), "search_document", ["gtin"])
    op.create_table(
        "search_processed_events",
        sa.Column("event_id", sa.String(length=26), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX ix_search_document_text_trgm ON search_document "
            "USING gin (search_text gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_search_document_text_trgm")
    op.drop_table("search_processed_events")
    op.drop_index(op.f("ix_search_document_gtin"), table_name="search_document")
    op.drop_index(op.f("ix_search_document_articul"), table_name="search_document")
    op.drop_index(op.f("ix_search_document_external_code"), table_name="search_document")
    op.drop_index(op.f("ix_search_document_supplier_code"), table_name="search_document")
    op.drop_table("search_document")
