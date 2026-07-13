"""Data access for supplier products (upsert on ingest, cursor-paginated reads)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.adapters.models import (
    CanonicalProductRow,
    ProductCanonicalLink,
    SupplierProductRow,
)
from catalog.domain.canonical import MemberProduct, build_canonical_card
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered
from sa_core.gtin import normalize_gtin
from sa_core.pagination import decode_cursor, encode_cursor
from sa_core.time import utc_now


async def upsert_supplier_product(session: AsyncSession, data: SupplierProductDiscovered) -> None:
    """Insert or update a supplier product from a discovered/updated event payload."""
    row = await session.get(SupplierProductRow, data.supplier_product_id)
    if row is None:
        session.add(
            SupplierProductRow(
                supplier_product_id=data.supplier_product_id,
                supplier_code=data.supplier_code,
                external_id=data.external_id,
                external_code=data.external_code,
                articul=data.articul,
                gtin=data.gtin,
                name=data.name,
                brand=data.brand,
                supplier_category_id=data.supplier_category_id,
                attributes=data.attributes or {},
                raw_identifiers=data.raw_identifiers or {},
            )
        )
        return
    row.external_code = data.external_code
    row.articul = data.articul
    row.gtin = data.gtin
    row.name = data.name
    row.brand = data.brand
    row.supplier_category_id = data.supplier_category_id
    row.attributes = data.attributes or {}
    row.raw_identifiers = data.raw_identifiers or {}
    row.updated_at = utc_now()


async def get_supplier_product(
    session: AsyncSession, supplier_product_id: str
) -> SupplierProductRow | None:
    return await session.get(SupplierProductRow, supplier_product_id)


async def set_canonical_link(
    session: AsyncSession, *, supplier_product_id: str, canonical_product_id: str
) -> None:
    """Record (or update) a supplier product's canonical mapping (from a link event)."""
    row = await session.get(ProductCanonicalLink, supplier_product_id)
    if row is None:
        session.add(
            ProductCanonicalLink(
                supplier_product_id=supplier_product_id,
                canonical_product_id=canonical_product_id,
            )
        )
        return
    row.canonical_product_id = canonical_product_id
    row.updated_at = utc_now()


async def rebuild_canonical_card(
    session: AsyncSession, canonical_product_id: str
) -> tuple[CanonicalProductRow, list[str]] | None:
    """Rebuild a canonical product's card from its current member supplier products (upsert).

    Returns the row and its sorted member ids, or ``None`` if no member products are present yet
    (e.g. a link arrived before its product was ingested) — nothing to emit in that case.
    """
    member_ids_stmt = select(ProductCanonicalLink.supplier_product_id).where(
        ProductCanonicalLink.canonical_product_id == canonical_product_id
    )
    rows = (
        (
            await session.execute(
                select(SupplierProductRow).where(
                    SupplierProductRow.supplier_product_id.in_(member_ids_stmt)
                )
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return None

    card = build_canonical_card(
        [
            MemberProduct(
                supplier_product_id=row.supplier_product_id,
                name=row.name,
                brand=row.brand,
                gtin=normalize_gtin(row.gtin),
                attributes=row.attributes or {},
            )
            for row in rows
        ]
    )
    member_ids = sorted(row.supplier_product_id for row in rows)

    canonical = await session.get(CanonicalProductRow, canonical_product_id)
    if canonical is None:
        canonical = CanonicalProductRow(canonical_product_id=canonical_product_id)
        session.add(canonical)
    canonical.title = card.title
    canonical.brand = card.brand
    canonical.gtin = card.gtin
    canonical.attributes = card.attributes
    canonical.supplier_product_ids = member_ids
    canonical.status = "confirmed"
    canonical.updated_at = utc_now()
    return canonical, member_ids


async def canonical_ids_for(
    session: AsyncSession, supplier_product_ids: Sequence[str]
) -> dict[str, str]:
    """Map supplier_product_id -> canonical_product_id for the given ids (missing omitted)."""
    if not supplier_product_ids:
        return {}
    stmt = select(
        ProductCanonicalLink.supplier_product_id, ProductCanonicalLink.canonical_product_id
    ).where(ProductCanonicalLink.supplier_product_id.in_(supplier_product_ids))
    return dict((await session.execute(stmt)).all())  # type: ignore[arg-type]


async def list_supplier_products(
    session: AsyncSession,
    *,
    supplier_code: str | None = None,
    canonical_product_id: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[Sequence[SupplierProductRow], str | None]:
    """Return a page of supplier products (ordered by id) and the next cursor, if any."""
    stmt = select(SupplierProductRow).order_by(SupplierProductRow.supplier_product_id).limit(limit)
    if supplier_code is not None:
        stmt = stmt.where(SupplierProductRow.supplier_code == supplier_code)
    if canonical_product_id is not None:
        linked = select(ProductCanonicalLink.supplier_product_id).where(
            ProductCanonicalLink.canonical_product_id == canonical_product_id
        )
        stmt = stmt.where(SupplierProductRow.supplier_product_id.in_(linked))
    if cursor is not None:
        after = str(decode_cursor(cursor)["after"])
        stmt = stmt.where(SupplierProductRow.supplier_product_id > after)

    rows = (await session.execute(stmt)).scalars().all()
    next_cursor = (
        encode_cursor({"after": rows[-1].supplier_product_id}) if len(rows) == limit else None
    )
    return rows, next_cursor
