"""Service-owned tables (on the shared persistence Base).

``SupplierProductIdentity`` gives every Brain product a stable internal
``supplier_product_id`` (ULID) keyed by ``(supplier_code, external_id)`` — so the id and
its emitted events stay consistent across re-syncs. ``content_hash`` drives change
detection. The ``outbox`` table comes from ``sa_persistence``.
"""

from __future__ import annotations

from datetime import datetime

from sa_persistence.db import Base
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from sa_core.time import utc_now


class SupplierProductIdentity(Base):
    """Stable identity + last-seen content fingerprint for a supplier product."""

    __tablename__ = "supplier_product_identity"

    supplier_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    supplier_product_id: Mapped[str] = mapped_column(String(26), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OfferIdentity(Base):
    """Stable ``offer_id`` per (account, product) plus the last observed price.

    The last price/currency drive change detection so we emit ``supplier.offer.price-changed``
    only when the price actually moved.
    """

    __tablename__ = "offer_identity"

    supplier_account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(26), unique=True)
    last_price: Mapped[str] = mapped_column(String(32))
    last_currency: Mapped[str] = mapped_column(String(3))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SyncWatermark(Base):
    """Last successful sync time per account — the baseline for the next delta sync.

    A delta sync fetches everything the supplier reports changed since this timestamp; it is
    advanced to the moment a sync started (not finished), so changes made mid-sync are re-caught
    next time rather than missed.
    """

    __tablename__ = "sync_watermark"

    supplier_code: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
