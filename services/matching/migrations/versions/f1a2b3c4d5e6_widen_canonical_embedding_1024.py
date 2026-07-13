"""widen canonical_product.embedding to 1024 (bge-m3)

Destructive migration: pgvector cannot cast between vector widths, so switching the embedding
model from the 256-dim stand-in to BAAI/bge-m3 (1024-dim) means dropping and re-adding the
column. Existing embeddings are discarded — after deploy, re-index by replaying
``supplier.product.discovered`` (canonicals are re-embedded on ingest). Ships in a dedicated
PR (see the embedder swap) per the expand-migrate-contract rule for destructive changes.

Revision ID: f1a2b3c4d5e6
Revises: b1c2d3e4f5a6
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match matching.domain.embedding.EMBEDDING_DIM (native width of BAAI/bge-m3).
_DIM = 1024
_OLD_DIM = 256
_INDEX = "ix_canonical_product_embedding"


def _rebuild(dim: int) -> None:
    op.drop_index(_INDEX, table_name="canonical_product")
    op.drop_column("canonical_product", "embedding")
    op.add_column("canonical_product", sa.Column("embedding", Vector(dim), nullable=True))
    op.create_index(
        _INDEX,
        "canonical_product",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def upgrade() -> None:
    _rebuild(_DIM)


def downgrade() -> None:
    _rebuild(_OLD_DIM)
