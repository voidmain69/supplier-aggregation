"""Offer identity resolution + price-change detection.

Mints a stable ``offer_id`` per (account, product) on first sight and reports whether the
price moved since last sync. Runs in the caller's transaction alongside the outbox enqueue.
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from connector_brain.adapters.models import OfferIdentity, SupplierProductIdentity
from sa_core.ids import new_ulid
from sa_core.money import Money
from sa_core.time import utc_now

OfferState = Literal["new", "changed", "unchanged"]


def price_str(price: Money) -> str:
    """Canonical 4-decimal string form of a price (matches the event schema pattern)."""
    return f"{price.amount:.4f}"


async def find_supplier_product_id(
    session: AsyncSession, *, supplier_code: str, external_id: str
) -> str | None:
    """Return the product's stable supplier_product_id, or None if not yet discovered."""
    row = await session.get(SupplierProductIdentity, (supplier_code, external_id))
    return row.supplier_product_id if row is not None else None


async def resolve_offer_and_stage(
    session: AsyncSession,
    *,
    supplier_account_id: str,
    external_id: str,
    price: Money,
) -> tuple[str, str | None, OfferState]:
    """Return ``(offer_id, old_price, state)`` and stage identity/price changes.

    - ``new`` — first sight; a fresh offer_id is minted, old_price is None.
    - ``changed`` — price or currency differs; old_price is the previous value.
    - ``unchanged`` — nothing moved.
    """
    new_price = price_str(price)
    row = await session.get(OfferIdentity, (supplier_account_id, external_id))
    if row is None:
        offer_id = new_ulid()
        session.add(
            OfferIdentity(
                supplier_account_id=supplier_account_id,
                external_id=external_id,
                offer_id=offer_id,
                last_price=new_price,
                last_currency=price.currency,
            )
        )
        return offer_id, None, "new"

    if row.last_price != new_price or row.last_currency != price.currency:
        old_price = row.last_price
        row.last_price = new_price
        row.last_currency = price.currency
        row.updated_at = utc_now()
        return row.offer_id, old_price, "changed"

    return row.offer_id, row.last_price, "unchanged"
