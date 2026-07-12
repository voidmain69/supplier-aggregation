"""Offer tables (on the shared persistence Base).

``OfferRow`` is the offer service's copy of each supplier offer (a price for one product
under one account), built from ``supplier.offer.price-changed`` events. ``SupplierAccountRow``
holds each account's financial terms (used to compute the effective price). ``ProcessedEvent``
makes consumption idempotent.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sa_persistence.db import Base
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from sa_core.time import utc_now

_MONEY = Numeric(14, 4)
_RATE = Numeric(18, 8)  # discount/markup fractions and FX rate need more scale than money


class OfferRow(Base):
    """A supplier offer: the current price/availability for one product under one account."""

    __tablename__ = "offer"

    offer_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    supplier_account_id: Mapped[str] = mapped_column(String(26), index=True)
    supplier_product_id: Mapped[str] = mapped_column(String(26), index=True)
    price: Mapped[Decimal] = mapped_column(_MONEY)
    currency: Mapped[str] = mapped_column(String(3))
    price_uah: Mapped[Decimal | None] = mapped_column(_MONEY, default=None)
    rrp_uah: Mapped[Decimal | None] = mapped_column(_MONEY, default=None)
    effective_price_uah: Mapped[Decimal | None] = mapped_column(_MONEY, default=None, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SupplierAccountRow(Base):
    """Financial terms for one supplier account (sensitive — hard rule 6, never logged)."""

    __tablename__ = "supplier_account"

    supplier_account_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    discount_pct: Mapped[Decimal] = mapped_column(_RATE, default=Decimal(0))
    markup_pct: Mapped[Decimal] = mapped_column(_RATE, default=Decimal(0))
    fx_rate_to_uah: Mapped[Decimal | None] = mapped_column(_RATE, default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    """An event id the offer service has already handled (consumer dedupe)."""

    __tablename__ = "offer_processed_events"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
