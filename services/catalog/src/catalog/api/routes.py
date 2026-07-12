"""Read API for supplier products — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.adapters.repository import (
    canonical_ids_for,
    get_supplier_product,
    list_supplier_products,
)
from catalog.api.deps import get_session
from catalog.api.schemas import Problem, SupplierProductOut
from sa_core.errors import NotFoundError
from sa_core.pagination import Page

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No supplier product with that id."}
}

router = APIRouter(prefix="/v1", tags=["supplier-products"])


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
