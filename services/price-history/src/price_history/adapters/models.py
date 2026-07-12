"""Price-history tables (on the shared persistence Base).

``PricePointRow`` is an append-only time series of supplier prices, one row per observed
price change. In production it is a TimescaleDB hypertable partitioned by ``ts`` (see
``db.create_schema``); on plain Postgres it is an ordinary table with the same shape, so
the queries are identical. The composite key ``(offer_id, ts)`` is Timescale-compatible.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sa_persistence.db import Base
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from sa_core.time import utc_now

_MONEY = Numeric(14, 4)


class PricePointRow(Base):
    """One observed price for an offer at a point in time."""

    __tablename__ = "price_point"

    offer_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    supplier_account_id: Mapped[str] = mapped_column(String(26))
    supplier_product_id: Mapped[str] = mapped_column(String(26), index=True)
    price: Mapped[Decimal] = mapped_column(_MONEY)
    currency: Mapped[str] = mapped_column(String(3))
    price_uah: Mapped[Decimal | None] = mapped_column(_MONEY, default=None)


class EffectivePricePointRow(Base):
    """One observed effective UAH price for an offer at a point in time (append-only).

    Fed by ``offer.effective-price.changed`` — a separate series from the raw supplier price so
    the two never collide on ``(offer_id, ts)``. Timescale-compatible composite key, like
    ``price_point``.
    """

    __tablename__ = "effective_price_point"

    offer_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    supplier_account_id: Mapped[str] = mapped_column(String(26))
    supplier_product_id: Mapped[str] = mapped_column(String(26), index=True)
    effective_price_uah: Mapped[Decimal] = mapped_column(_MONEY)
    base_price: Mapped[Decimal] = mapped_column(_MONEY)
    currency: Mapped[str] = mapped_column(String(3))
    cause: Mapped[str] = mapped_column(String(16))


class ProcessedEvent(Base):
    """An event id the price-history service has already handled (consumer dedupe)."""

    __tablename__ = "price_history_processed_events"

    event_id: Mapped[str] = mapped_column(String(26), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
