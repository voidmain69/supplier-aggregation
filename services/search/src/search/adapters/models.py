"""Search index tables (on the shared persistence Base).

``SearchDocumentRow`` is one indexed product — currently supplier products, built from
``supplier.product.discovered`` events. ``search_text`` is the lowercased, tokenized bag of
name/brand/articul/codes that lexical queries match against. ``ProcessedEvent`` makes indexing
idempotent.
"""

from __future__ import annotations

from datetime import datetime

from pgvector import SparseVector
from pgvector.sqlalchemy import SPARSEVEC, Vector
from sa_persistence.db import Base
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from sa_core.time import utc_now
from search.domain.embedding import EMBEDDING_DIM
from search.domain.sparse import SPARSE_DIM

# pgvector on Postgres; a portable JSON list on SQLite (unit tests) — same Python value.
_EMBEDDING = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")
# Learned-sparse (SPLADE) vector: pgvector sparsevec on Postgres, JSON on SQLite. Written only when
# a sparse embedder is configured (Postgres path); unit tests leave it null.
_SPARSE = SPARSEVEC(SPARSE_DIM).with_variant(JSON(), "sqlite")


class SearchDocumentRow(Base):
    """One indexed product: identifiers for exact lookup + a searchable text blob + embedding."""

    __tablename__ = "search_document"

    supplier_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    supplier_code: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    external_code: Mapped[str | None] = mapped_column(String(128), default=None, index=True)
    articul: Mapped[str | None] = mapped_column(String(256), default=None, index=True)
    gtin: Mapped[str | None] = mapped_column(String(14), default=None, index=True)
    name: Mapped[str] = mapped_column(String(512))
    brand: Mapped[str | None] = mapped_column(String(256), default=None)
    search_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(_EMBEDDING, default=None)
    embedding_sparse: Mapped[SparseVector | None] = mapped_column(_SPARSE, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CanonicalDocumentRow(Base):
    """One indexed canonical (platform) product, built from ``catalog.product.updated`` events.

    The searchable projection of the catalog's canonical card — so semantic/hybrid search can
    return canonical product ids (the platform's own products), not just supplier products.
    """

    __tablename__ = "canonical_document"

    canonical_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    gtin: Mapped[str | None] = mapped_column(String(14), default=None, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    brand: Mapped[str | None] = mapped_column(String(256), default=None)
    search_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(_EMBEDDING, default=None)
    embedding_sparse: Mapped[SparseVector | None] = mapped_column(_SPARSE, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    """An event id the search service has already indexed (consumer dedupe)."""

    __tablename__ = "search_processed_events"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
