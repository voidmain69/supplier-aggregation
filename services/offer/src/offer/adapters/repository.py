"""Data access for offers (upsert on ingest, reads by product, best offer)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from offer.adapters.models import OfferRow
from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import ensure_utc, utc_now


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


async def upsert_offer(session: AsyncSession, data: SupplierOfferPriceChanged) -> None:
    """Insert or update an offer from a price-changed event."""
    observed_at = ensure_utc(data.observed_at)
    row = await session.get(OfferRow, data.offer_id)
    if row is None:
        session.add(
            OfferRow(
                offer_id=data.offer_id,
                supplier_account_id=data.supplier_account_id,
                supplier_product_id=data.supplier_product_id,
                price=Decimal(data.new_price),
                currency=data.currency,
                price_uah=_decimal(data.price_uah),
                rrp_uah=_decimal(data.rrp_uah),
                observed_at=observed_at,
            )
        )
        return
    row.price = Decimal(data.new_price)
    row.currency = data.currency
    row.price_uah = _decimal(data.price_uah)
    row.rrp_uah = _decimal(data.rrp_uah)
    row.observed_at = observed_at
    row.updated_at = utc_now()


async def get_offer(session: AsyncSession, offer_id: str) -> OfferRow | None:
    return await session.get(OfferRow, offer_id)


async def list_offers_for_product(
    session: AsyncSession,
    supplier_product_id: str,
    *,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[Sequence[OfferRow], str | None]:
    """Offers for a canonical/supplier product, ordered by offer_id (cursor-paginated)."""
    stmt = (
        select(OfferRow)
        .where(OfferRow.supplier_product_id == supplier_product_id)
        .order_by(OfferRow.offer_id)
        .limit(limit)
    )
    if cursor is not None:
        stmt = stmt.where(OfferRow.offer_id > str(decode_cursor(cursor)["after"]))
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = encode_cursor({"after": rows[-1].offer_id}) if len(rows) == limit else None
    return rows, next_cursor


async def best_offer_for_product(
    session: AsyncSession, supplier_product_id: str
) -> OfferRow | None:
    """The cheapest offer (by UAH price) for a product, or None if none has a UAH price."""
    stmt = (
        select(OfferRow)
        .where(
            OfferRow.supplier_product_id == supplier_product_id,
            OfferRow.price_uah.is_not(None),
        )
        .order_by(OfferRow.price_uah)
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()
