"""add canonical_product.embedding (pgvector)

Additive migration (expand): enable the pgvector extension, add the embedding column used
for nearest-neighbour candidate search, and index it for cosine distance.

Revision ID: b1c2d3e4f5a6
Revises: 80926a91aa7f
Create Date: 2026-07-12 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "80926a91aa7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match matching.domain.embedding.EMBEDDING_DIM (changing the width is a new migration).
_DIM = 256


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("canonical_product", sa.Column("embedding", Vector(_DIM), nullable=True))
    op.create_index(
        "ix_canonical_product_embedding",
        "canonical_product",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_canonical_product_embedding", table_name="canonical_product")
    op.drop_column("canonical_product", "embedding")
