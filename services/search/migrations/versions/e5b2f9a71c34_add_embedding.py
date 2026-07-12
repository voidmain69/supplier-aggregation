"""add search_document.embedding (pgvector)

Additive migration (expand): enable the pgvector extension, add the embedding column used for
semantic nearest-neighbour search, and index it for cosine distance.

Revision ID: e5b2f9a71c34
Revises: a1c4e8b06f92
Create Date: 2026-07-12 20:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "e5b2f9a71c34"
down_revision: str | None = "a1c4e8b06f92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match search.domain.embedding.EMBEDDING_DIM (changing the width is a new migration).
_DIM = 256


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("search_document", sa.Column("embedding", Vector(_DIM), nullable=True))
    op.create_index(
        "ix_search_document_embedding",
        "search_document",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_search_document_embedding", table_name="search_document")
    op.drop_column("search_document", "embedding")
