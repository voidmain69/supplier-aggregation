"""Catalog tables (on the shared persistence Base).

``SupplierProductRow`` is the catalog's own copy of each supplier product, built from
``supplier.product.discovered`` events. ``ProcessedEvent`` records handled event ids so
consumption is idempotent (hard rule 3).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sa_persistence.db import Base
from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from sa_core.time import utc_now


class SupplierProductRow(Base):
    """A supplier product as ingested by the catalog."""

    __tablename__ = "supplier_product"
    __table_args__ = (UniqueConstraint("supplier_code", "external_id"),)

    supplier_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    supplier_code: Mapped[str] = mapped_column(String(64), index=True)
    external_id: Mapped[str] = mapped_column(String(128))
    external_code: Mapped[str | None] = mapped_column(String(128), default=None)
    articul: Mapped[str | None] = mapped_column(String(255), default=None)
    gtin: Mapped[str | None] = mapped_column(String(14), default=None, index=True)
    name: Mapped[str] = mapped_column(String(1024))
    brand: Mapped[str | None] = mapped_column(String(255), default=None)
    supplier_category_id: Mapped[str | None] = mapped_column(String(64), default=None)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    raw_identifiers: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CanonicalProductRow(Base):
    """The platform's canonical product card, owned by the catalog and rebuilt from its members.

    Built by aggregating the supplier products linked to it (see domain.canonical); emitted as
    ``catalog.product.updated`` for search indexing and offer cache invalidation. Named
    ``catalog_product`` (not ``canonical_product``) because table names are globally unique on the
    shared persistence Base, and matching keeps its own ``canonical_product`` (RAG embedding) table.
    """

    __tablename__ = "catalog_product"

    canonical_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    gtin: Mapped[str | None] = mapped_column(String(14), default=None, index=True)
    brand: Mapped[str | None] = mapped_column(String(255), default=None)
    title: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(16), default="confirmed")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    supplier_product_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProductCanonicalLink(Base):
    """Which canonical product a supplier product maps to (from matching.link.confirmed).

    Kept in its own table so a link event that arrives before its product is ingested is
    never lost (no ordering dependency between the two consumers).
    """

    __tablename__ = "product_canonical_link"

    supplier_product_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    canonical_product_id: Mapped[str] = mapped_column(String(26), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    """An event id the catalog has already handled (consumer dedupe)."""

    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
