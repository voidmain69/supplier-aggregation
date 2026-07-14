"""Read API for supplier products — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.adapters.repository import (
    canonical_ids_for,
    get_canonical_product,
    get_supplier_product,
    list_canonical_products,
    list_supplier_products,
)
from catalog.api.deps import get_session
from catalog.api.schemas import CanonicalProductOut, Problem, SupplierProductOut
from sa_core.errors import NotFoundError
from sa_core.pagination import Page

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No supplier product with that id."}
}
_CANONICAL_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No canonical product with that id."}
}

router = APIRouter(prefix="/v1", tags=["supplier-products"])
canonical_router = APIRouter(prefix="/v1", tags=["canonical-products"])


@router.get(
    "/supplier-products",
    operation_id="listSupplierProducts",
    summary="List supplier products",
    description=(
        "List supplier products the catalog has ingested, newest-id first. Cursor "
        "paginated: pass the returned next_cursor to fetch the following page. Filter by "
        "supplier code, or by canonical_product_id to get every supplier's version of one "
        "canonical product."
    ),
    response_model=Page[SupplierProductOut],
)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    supplier: Annotated[
        str | None, Query(description="Filter by supplier code, e.g. 'brain'.")
    ] = None,
    canonical_product_id: Annotated[
        str | None,
        Query(description="Filter to supplier products mapped to this canonical product (ULID)."),
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items per page (1-200, default 50).")
    ] = 50,
) -> Page[SupplierProductOut]:
    rows, next_cursor = await list_supplier_products(
        session,
        supplier_code=supplier,
        canonical_product_id=canonical_product_id,
        cursor=cursor,
        limit=limit,
    )
    canonical = await canonical_ids_for(session, [r.supplier_product_id for r in rows])
    items = [
        SupplierProductOut.from_row(r, canonical_product_id=canonical.get(r.supplier_product_id))
        for r in rows
    ]
    return Page(items=items, next_cursor=next_cursor)


@router.get(
    "/supplier-products/{supplier_product_id}",
    operation_id="getSupplierProduct",
    summary="Get one supplier product",
    description="Fetch a single supplier product by its internal supplier_product_id (ULID).",
    response_model=SupplierProductOut,
    responses=_NOT_FOUND,
)
async def get_product(
    supplier_product_id: Annotated[
        str, Path(description="Internal supplier_product_id (ULID) from a list response.")
    ],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupplierProductOut:
    row = await get_supplier_product(session, supplier_product_id)
    if row is None:
        raise NotFoundError(
            f"No supplier product with id {supplier_product_id}. "
            "List live ids via GET /v1/supplier-products.",
            instance=f"/v1/supplier-products/{supplier_product_id}",
        )
    canonical = await canonical_ids_for(session, [supplier_product_id])
    return SupplierProductOut.from_row(row, canonical_product_id=canonical.get(supplier_product_id))


@canonical_router.get(
    "/canonical-products",
    operation_id="listCanonicalProducts",
    summary="List canonical products",
    description=(
        "List canonical (platform) product cards the catalog owns, optionally filtered by "
        "normalized GTIN-14. Cursor paginated: pass the returned next_cursor to fetch the "
        "following page. Each card is the deterministic merge of its member supplier products."
    ),
    response_model=Page[CanonicalProductOut],
)
async def list_canonical(
    session: Annotated[AsyncSession, Depends(get_session)],
    gtin: Annotated[
        str | None, Query(description="Filter by normalized GTIN-14 (14 digits).")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items per page (1-200, default 50).")
    ] = 50,
) -> Page[CanonicalProductOut]:
    rows, next_cursor = await list_canonical_products(
        session, gtin=gtin, cursor=cursor, limit=limit
    )
    return Page(items=[CanonicalProductOut.from_row(r) for r in rows], next_cursor=next_cursor)


@canonical_router.get(
    "/canonical-products/{canonical_product_id}",
    operation_id="getCanonicalProduct",
    summary="Get one canonical product",
    description=(
        "Fetch a single canonical product card by its internal canonical_product_id (ULID), "
        "including merged attributes and the member supplier_product_ids."
    ),
    response_model=CanonicalProductOut,
    responses=_CANONICAL_NOT_FOUND,
)
async def get_canonical(
    canonical_product_id: Annotated[str, Path(description="Internal canonical_product_id (ULID).")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CanonicalProductOut:
    row = await get_canonical_product(session, canonical_product_id)
    if row is None:
        raise NotFoundError(
            f"No canonical product with id {canonical_product_id}. "
            "List ids via GET /v1/canonical-products.",
            instance=f"/v1/canonical-products/{canonical_product_id}",
        )
    return CanonicalProductOut.from_row(row)
