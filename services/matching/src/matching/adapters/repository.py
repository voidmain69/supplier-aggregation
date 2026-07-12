"""Data access for canonical products and product links."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.models import CanonicalProductRow, ProductLinkRow
from sa_core.ids import new_ulid
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import utc_now


async def find_canonical_by_gtin(session: AsyncSession, gtin: str) -> CanonicalProductRow | None:
    stmt = select(CanonicalProductRow).where(CanonicalProductRow.gtin == gtin)
    return (await session.execute(stmt)).scalars().first()


async def get_canonical(
    session: AsyncSession, canonical_product_id: str
) -> CanonicalProductRow | None:
    return await session.get(CanonicalProductRow, canonical_product_id)


def create_canonical(
    session: AsyncSession, *, gtin: str | None, brand: str | None, title: str
) -> CanonicalProductRow:
    """Create a canonical product (app-minted ULID; not yet flushed)."""
    row = CanonicalProductRow(canonical_product_id=new_ulid(), gtin=gtin, brand=brand, title=title)
    session.add(row)
    return row


def create_link(
    session: AsyncSession,
    *,
    supplier_product_id: str,
    canonical_product_id: str,
    method: str,
    confidence: float,
    status: str,
    decided_by: str,
) -> ProductLinkRow:
    """Create the link for a supplier product (called once per product; app-minted ids)."""
    row = ProductLinkRow(
        supplier_product_id=supplier_product_id,
        canonical_product_id=canonical_product_id,
        link_id=new_ulid(),
        method=method,
        confidence=confidence,
        status=status,
        decided_by=decided_by,
        decided_at=utc_now(),
    )
    session.add(row)
    return row


async def get_link(session: AsyncSession, supplier_product_id: str) -> ProductLinkRow | None:
    return await session.get(ProductLinkRow, supplier_product_id)


async def list_canonical(
    session: AsyncSession,
    *,
    gtin: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[Sequence[CanonicalProductRow], str | None]:
    stmt = (
        select(CanonicalProductRow).order_by(CanonicalProductRow.canonical_product_id).limit(limit)
    )
    if gtin is not None:
        stmt = stmt.where(CanonicalProductRow.gtin == gtin)
    if cursor is not None:
        stmt = stmt.where(
            CanonicalProductRow.canonical_product_id > str(decode_cursor(cursor)["after"])
        )
    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = (
        encode_cursor({"after": rows[-1].canonical_product_id}) if len(rows) == limit else None
    )
    return rows, next_cursor
