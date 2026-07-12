"""Data access for supplier products (upsert on ingest, cursor-paginated reads)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.adapters.models import ProductCanonicalLink, SupplierProductRow
from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered
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
