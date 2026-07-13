"""Data access for offers (upsert on ingest, reads by product, best offer) + account terms."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sa_persistence.outbox import enqueue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from offer.adapters.models import OfferRow, SupplierAccountRow
from offer.domain.pricing import DEFAULT_TERMS, FinancialTerms, effective_price_uah
from offer.events.mapping import Cause, effective_price_changed_record
from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import ensure_utc, utc_now


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _emit_effective_change(
    session: AsyncSession,
    *,
    offer: OfferRow,
    old_effective: Decimal | None,
    new_effective: Decimal | None,
    observed_at: datetime,
    cause: Cause,
) -> None:
    """Stage an effective-price-changed event when the price actually moved to a UAH value.

    A move to None (offer can no longer be priced in UAH) has no valid event representation,
    so it is not emitted; the stored effective_price_uah still reflects it.
    """
    if new_effective is None or new_effective == old_effective:
        return
    enqueue(
        session,
        effective_price_changed_record(
            offer_id=offer.offer_id,
            supplier_account_id=offer.supplier_account_id,
            supplier_product_id=offer.supplier_product_id,
            old_effective=old_effective,
            new_effective=new_effective,
            base_price=offer.price,
            currency=offer.currency,
            observed_at=observed_at,
            cause=cause,
        ),
    )


def _terms_of(row: SupplierAccountRow | None) -> FinancialTerms:
    if row is None:
        return DEFAULT_TERMS
    return FinancialTerms(
        discount_pct=row.discount_pct,
        markup_pct=row.markup_pct,
        fx_rate_to_uah=row.fx_rate_to_uah,
    )


async def get_account_terms(session: AsyncSession, account_id: str) -> FinancialTerms:
    """Return the account's financial terms, or the platform defaults if none are set."""
    return _terms_of(await session.get(SupplierAccountRow, account_id))


async def upsert_offer(session: AsyncSession, data: SupplierOfferPriceChanged) -> None:
    """Insert or update an offer from a price-changed event, computing its effective price."""
    observed_at = ensure_utc(data.observed_at)
    price = Decimal(data.new_price)
    price_uah = _decimal(data.price_uah)
    terms = await get_account_terms(session, data.supplier_account_id)
    effective = effective_price_uah(
        base_price=price,
        currency=data.currency,
        terms=terms,
        supplier_price_uah=price_uah,
    )
    row = await session.get(OfferRow, data.offer_id)
    old_effective = row.effective_price_uah if row is not None else None
    if row is None:
        row = OfferRow(
            offer_id=data.offer_id,
            supplier_account_id=data.supplier_account_id,
            supplier_product_id=data.supplier_product_id,
            price=price,
            currency=data.currency,
            price_uah=price_uah,
            rrp_uah=_decimal(data.rrp_uah),
            effective_price_uah=effective,
            observed_at=observed_at,
        )
        session.add(row)
    else:
        row.price = price
        row.currency = data.currency
        row.price_uah = price_uah
        row.rrp_uah = _decimal(data.rrp_uah)
        row.effective_price_uah = effective
        row.observed_at = observed_at
        row.updated_at = utc_now()
    _emit_effective_change(
        session,
        offer=row,
        old_effective=old_effective,
        new_effective=effective,
        observed_at=observed_at,
        cause="price_changed",
    )


async def upsert_account_terms(
    session: AsyncSession, account_id: str, terms: FinancialTerms
) -> int:
    """Store an account's financial terms and re-price its offers. Returns offers re-priced."""
    row = await session.get(SupplierAccountRow, account_id)
    if row is None:
        session.add(
            SupplierAccountRow(
                supplier_account_id=account_id,
                discount_pct=terms.discount_pct,
                markup_pct=terms.markup_pct,
                fx_rate_to_uah=terms.fx_rate_to_uah,
            )
        )
    else:
        row.discount_pct = terms.discount_pct
        row.markup_pct = terms.markup_pct
        row.fx_rate_to_uah = terms.fx_rate_to_uah
        row.updated_at = utc_now()
    await session.flush()
    return await _reprice_account(session, account_id, terms)


async def _reprice_account(session: AsyncSession, account_id: str, terms: FinancialTerms) -> int:
    """Recompute effective_price_uah for every offer of an account after a terms change."""
    now = utc_now()
    stmt = select(OfferRow).where(OfferRow.supplier_account_id == account_id)
    rows = (await session.execute(stmt)).scalars().all()
    for row in rows:
        old_effective = row.effective_price_uah
        new_effective = effective_price_uah(
            base_price=row.price,
            currency=row.currency,
            terms=terms,
            supplier_price_uah=row.price_uah,
        )
        row.effective_price_uah = new_effective
        row.updated_at = now
        _emit_effective_change(
            session,
            offer=row,
            old_effective=old_effective,
            new_effective=new_effective,
            observed_at=now,
            cause="terms_changed",
        )
    return len(rows)


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
    """The cheapest offer (by effective UAH price) for a product, or None if none is priced."""
    stmt = (
        select(OfferRow)
        .where(
            OfferRow.supplier_product_id == supplier_product_id,
            OfferRow.effective_price_uah.is_not(None),
        )
        .order_by(OfferRow.effective_price_uah)
        .limit(1)
    )
    return (await session.execute(stmt)).scalars().first()
