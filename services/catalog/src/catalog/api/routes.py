"""Read API for supplier products — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from catalog.adapters.repository import get_supplier_product, list_supplier_products
from catalog.api.deps import get_session
from catalog.api.schemas import SupplierProductOut
from sa_core.errors import NotFoundError
from sa_core.pagination import Page

router = APIRouter(prefix="/v1", tags=["supplier-products"])


@router.get(
    "/supplier-products",
    operation_id="listSupplierProducts",
    summary="List supplier products",
    description=(
        "List supplier products the catalog has ingested, newest-id first. Cursor "
        "paginated: pass the returned next_cursor to fetch the following page. Filter by "
        "supplier with the 'supplier' query param."
    ),
    response_model=Page[SupplierProductOut],
)
async def list_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    supplier: Annotated[
        str | None, Query(description="Filter by supplier code, e.g. 'brain'.")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items per page (1-200, default 50).")
    ] = 50,
) -> Page[SupplierProductOut]:
    rows, next_cursor = await list_supplier_products(
        session, supplier_code=supplier, cursor=cursor, limit=limit
    )
    return Page(items=[SupplierProductOut.from_row(r) for r in rows], next_cursor=next_cursor)


@router.get(
    "/supplier-products/{supplier_product_id}",
    operation_id="getSupplierProduct",
    summary="Get one supplier product",
    description="Fetch a single supplier product by its internal supplier_product_id (ULID).",
    response_model=SupplierProductOut,
)
async def get_product(
    supplier_product_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupplierProductOut:
    row = await get_supplier_product(session, supplier_product_id)
    if row is None:
        raise NotFoundError(
            f"No supplier product with id {supplier_product_id}. "
            "List live ids via GET /v1/supplier-products.",
            instance=f"/v1/supplier-products/{supplier_product_id}",
        )
    return SupplierProductOut.from_row(row)
