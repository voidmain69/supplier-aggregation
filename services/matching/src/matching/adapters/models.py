"""Matching tables (on the shared persistence Base).

``CanonicalProductRow`` is the platform's own product, aggregating supplier products that
are the same thing. ``ProductLinkRow`` records which supplier product maps to which
canonical product and how it was decided. ``ProcessedEvent`` makes consumption idempotent.
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sa_persistence.db import Base
from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from matching.domain.embedding import EMBEDDING_DIM
from sa_core.time import utc_now

# pgvector on Postgres; a portable JSON list on SQLite (unit tests) — same Python value.
_EMBEDDING = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")


class CanonicalProductRow(Base):
    """A canonical (platform) product — the merge target for supplier products."""

    __tablename__ = "canonical_product"

    canonical_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    gtin: Mapped[str | None] = mapped_column(String(14), unique=True, default=None, index=True)
    brand: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    title: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="confirmed")  # confirmed | draft
    # Embedding of `canonical_text(title)` for nearest-neighbour candidate search.
    embedding: Mapped[list[float] | None] = mapped_column(_EMBEDDING, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProductLinkRow(Base):
    """A supplier product mapped to a canonical product, with how it was decided."""

    __tablename__ = "product_link"

    supplier_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    canonical_product_id: Mapped[str] = mapped_column(String(26), index=True)
    link_id: Mapped[str] = mapped_column(String(26), unique=True)
    method: Mapped[str] = mapped_column(String(16))  # gtin_auto | rag_suggested | manual
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))  # auto | pending_review | confirmed | rejected
    decided_by: Mapped[str] = mapped_column(String(64))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DecisionLogRow(Base):
    """An append-only audit record of one operator (or system) curation decision.

    Unlike ``ProductLinkRow`` (current state, overwritten on re-decision), this is history: every
    confirm / reject / create-new / merge is one immutable row, ordered by its ULID id (time).
    """

    __tablename__ = "decision_log"

    decision_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    action: Mapped[str] = mapped_column(String(16))  # confirm | reject | create_new | merge
    supplier_product_id: Mapped[str | None] = mapped_column(String(26), default=None, index=True)
    canonical_product_id: Mapped[str] = mapped_column(String(26))
    method: Mapped[str | None] = mapped_column(String(16), default=None)
    confidence: Mapped[float | None] = mapped_column(Float, default=None)
    operator: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(512), default=None)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    """An event id the matching service has already handled (consumer dedupe)."""

    __tablename__ = "matching_processed_events"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
