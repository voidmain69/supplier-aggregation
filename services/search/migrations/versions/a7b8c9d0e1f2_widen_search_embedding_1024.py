"""widen search_document.embedding to 1024 (bge-m3)

Destructive migration: pgvector cannot cast between vector widths, so switching the embedding
model from the 256-dim stand-in to BAAI/bge-m3 (1024-dim) means dropping and re-adding the
column. Existing embeddings are discarded — after deploy, re-index by replaying
``supplier.product.discovered`` (documents are re-embedded on ingest). Ships in a dedicated
PR (see the embedder swap) per the expand-migrate-contract rule for destructive changes.

Revision ID: a7b8c9d0e1f2
Revises: e5b2f9a71c34
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "e5b2f9a71c34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match search.domain.embedding.EMBEDDING_DIM (native width of BAAI/bge-m3).
_DIM = 1024
_OLD_DIM = 256
_INDEX = "ix_search_document_embedding"


def _rebuild(dim: int) -> None:
    op.drop_index(_INDEX, table_name="search_document")
    op.drop_column("search_document", "embedding")
    op.add_column("search_document", sa.Column("embedding", Vector(dim), nullable=True))
    op.create_index(
        _INDEX,
        "search_document",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def upgrade() -> None:
    _rebuild(_DIM)


def downgrade() -> None:
    _rebuild(_OLD_DIM)
