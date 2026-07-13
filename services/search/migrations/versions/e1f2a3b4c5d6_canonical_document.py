"""add canonical_document (search index of canonical products)

Additive migration (expand): index canonical (platform) products, built from
``catalog.product.updated`` events, so semantic/hybrid search can return canonical product ids.
Mirrors search_document: dense pgvector embedding (cosine HNSW), SPLADE sparsevec (ip HNSW), and a
full-text GIN index. PostgreSQL-only index features; SQLite tests use the JSON/LIKE fallbacks.

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import SPARSEVEC, Vector
from search.domain.embedding import EMBEDDING_DIM
from search.domain.sparse import SPARSE_DIM

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_document",
        sa.Column("canonical_product_id", sa.String(length=26), nullable=False),
        sa.Column("gtin", sa.String(length=14), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("brand", sa.String(length=256), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("embedding_sparse", SPARSEVEC(SPARSE_DIM), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("canonical_product_id"),
    )
    op.create_index(
        op.f("ix_canonical_document_gtin"), "canonical_document", ["gtin"], unique=False
    )
    op.create_index(
        "ix_canonical_document_embedding",
        "canonical_document",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_canonical_document_embedding_sparse",
        "canonical_document",
        ["embedding_sparse"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding_sparse": "sparsevec_ip_ops"},
    )
    op.execute(
        "CREATE INDEX ix_canonical_document_fts ON canonical_document "
        "USING gin (to_tsvector('simple', search_text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_canonical_document_fts")
    op.drop_index("ix_canonical_document_embedding_sparse", table_name="canonical_document")
    op.drop_index("ix_canonical_document_embedding", table_name="canonical_document")
    op.drop_index(op.f("ix_canonical_document_gtin"), table_name="canonical_document")
    op.drop_table("canonical_document")
