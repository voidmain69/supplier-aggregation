"""Read API for offers — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from offer.adapters.repository import (
    best_offer_for_product,
    get_offer,
    list_offers_for_product,
)
from offer.api.deps import get_session
from offer.api.schemas import OfferOut, Problem
from sa_core.errors import NotFoundError
from sa_core.pagination import Page

router = APIRouter(prefix="/v1", tags=["offers"])

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No matching offer."}
}


@router.get(
    "/offers",
    operation_id="listOffers",
    summary="List offers for a product",
    description=(
        "List all supplier offers (one per account) for a product, identified by "
        "supplier_product_id. Cursor paginated. To get the cheapest, use /v1/offers/best."
    ),
    response_model=Page[OfferOut],
)
async def list_offers(
    session: Annotated[AsyncSession, Depends(get_session)],
    supplier_product_id: Annotated[
        str, Query(description="Internal product id (ULID) to list offers for.")
    ],
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items per page (1-200, default 50).")
    ] = 50,
) -> Page[OfferOut]:
    rows, next_cursor = await list_offers_for_product(
        session, supplier_product_id, cursor=cursor, limit=limit
    )
    return Page(items=[OfferOut.from_row(r) for r in rows], next_cursor=next_cursor)


@router.get(
    "/offers/best",
    operation_id="getBestOffer",
    summary="Get the cheapest offer for a product",
    description=(
        "Return the cheapest offer (lowest UAH price) for a product across all suppliers "
        "and accounts. 404 if the product has no offer with a UAH price."
    ),
    response_model=OfferOut,
    responses=_NOT_FOUND,
)
async def best_offer(
    session: Annotated[AsyncSession, Depends(get_session)],
    supplier_product_id: Annotated[str, Query(description="Internal product id (ULID) to price.")],
) -> OfferOut:
    row = await best_offer_for_product(session, supplier_product_id)
    if row is None:
        raise NotFoundError(
            f"No priced offer for product {supplier_product_id}. "
            "Check the id via the catalog service, or list offers at /v1/offers.",
            instance="/v1/offers/best",
        )
    return OfferOut.from_row(row)


@router.get(
    "/offers/{offer_id}",
    operation_id="getOffer",
    summary="Get one offer",
    description="Fetch a single offer by its internal offer_id (ULID).",
    response_model=OfferOut,
    responses=_NOT_FOUND,
)
async def get_one_offer(
    offer_id: Annotated[str, Path(description="Internal offer_id (ULID) from a list response.")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OfferOut:
    row = await get_offer(session, offer_id)
    if row is None:
        raise NotFoundError(
            f"No offer with id {offer_id}. List live ids via GET /v1/offers.",
            instance=f"/v1/offers/{offer_id}",
        )
    return OfferOut.from_row(row)
