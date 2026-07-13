"""add search_document full-text GIN index (to_tsvector)

Additive migration (expand): back the lexical full-text query in the search repository with a GIN
index on ``to_tsvector('simple', search_text)`` so FTS matching/ranking is index-supported at
scale. PostgreSQL-only (the index is functional over a tsvector); SQLite unit tests use the LIKE
fallback and do not run migrations. The query is correct without the index (seq scan) — this only
adds speed, per the portable-query/native-scale pattern ([ADR-0010]).

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match search.adapters.repository._FTS_CONFIG.
_INDEX = "ix_search_document_fts"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX {_INDEX} ON search_document USING gin (to_tsvector('simple', search_text))"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
