"""add search_document.embedding_sparse (pgvector sparsevec / SPLADE)

Additive migration (expand): add the learned-sparse (SPLADE) vector column used by the third
hybrid-search retriever, and an HNSW index for max-inner-product search. PostgreSQL-only
(sparsevec is a pgvector type); SQLite unit tests use the JSON variant and do not run migrations.
The column is nullable and populated only when a sparse embedder is configured — existing rows and
offline deployments are unaffected.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import SPARSEVEC
from search.domain.sparse import SPARSE_DIM

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_search_document_embedding_sparse"


def upgrade() -> None:
    op.add_column(
        "search_document", sa.Column("embedding_sparse", SPARSEVEC(SPARSE_DIM), nullable=True)
    )
    op.create_index(
        _INDEX,
        "search_document",
        ["embedding_sparse"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding_sparse": "sparsevec_ip_ops"},
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="search_document")
    op.drop_column("search_document", "embedding_sparse")
