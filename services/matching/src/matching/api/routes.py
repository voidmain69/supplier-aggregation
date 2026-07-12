"""Read API for canonical products — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.repository import get_canonical, list_canonical
from matching.api.deps import get_session
from matching.api.schemas import CanonicalProductOut, Problem
from sa_core.errors import NotFoundError
from sa_core.pagination import Page

router = APIRouter(prefix="/v1", tags=["canonical-products"])

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No canonical product with that id."}
}


@router.get(
    "/canonical-products",
    operation_id="listCanonicalProducts",
    summary="List canonical products",
    description=(
        "List canonical (platform) products, optionally filtered by normalized GTIN-14. "
        "Cursor paginated. Use it to find the canonical product that aggregates a GTIN."
    ),
    response_model=Page[CanonicalProductOut],
)
async def list_products(
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
    rows, next_cursor = await list_canonical(session, gtin=gtin, cursor=cursor, limit=limit)
    return Page(items=[CanonicalProductOut.from_row(r) for r in rows], next_cursor=next_cursor)


@router.get(
    "/canonical-products/{canonical_product_id}",
    operation_id="getCanonicalProduct",
    summary="Get one canonical product",
    description="Fetch a single canonical product by its internal canonical_product_id (ULID).",
    response_model=CanonicalProductOut,
    responses=_NOT_FOUND,
)
async def get_product(
    canonical_product_id: Annotated[str, Path(description="Internal canonical_product_id (ULID).")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CanonicalProductOut:
    row = await get_canonical(session, canonical_product_id)
    if row is None:
        raise NotFoundError(
            f"No canonical product with id {canonical_product_id}. "
            "List ids via GET /v1/canonical-products.",
            instance=f"/v1/canonical-products/{canonical_product_id}",
        )
    return CanonicalProductOut.from_row(row)
