"""Read API for canonical products — cursor-paginated, problem+json errors (AI-ready)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.repository import (
    delete_canonical,
    get_canonical,
    links_for_canonical,
    list_canonical,
    record_decision,
)
from matching.api.deps import get_session
from matching.api.schemas import (
    CanonicalProductOut,
    MergeCanonicalIn,
    MergeResultOut,
    Problem,
)
from matching.events.mapping import link_confirmed_record
from sa_core.errors import ConflictError, NotFoundError
from sa_core.pagination import Page
from sa_core.time import utc_now

router = APIRouter(prefix="/v1", tags=["canonical-products"])

# The operator identity is set by the API gateway (see curation.py); mirror it here.
_OPERATOR_HEADER = "X-Operator-Id"
_OPERATOR_FALLBACK = "operator"
# Link statuses already reflected downstream (catalog built a card) — repointing them re-emits.
_EMITTED_STATUSES = frozenset({"auto", "confirmed"})

_NOT_FOUND: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No canonical product with that id."}
}
_MERGE_ERRORS: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "Target or source canonical does not exist."},
    409: {"model": Problem, "description": "Source and target are the same product."},
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


@router.post(
    "/canonical-products/{canonical_product_id}/merge",
    operation_id="mergeCanonicalProducts",
    summary="Merge one canonical product into another",
    description=(
        "Fold the source canonical into this (target) one: every supplier-product link on the "
        "source is repointed to the target, then the source is removed. Use it when two canonical "
        "products are actually the same. Emits matching.link.confirmed for each already-linked "
        "supplier product so the catalog rebuilds against the target."
    ),
    response_model=MergeResultOut,
    responses=_MERGE_ERRORS,
)
async def merge_canonical_products(
    canonical_product_id: Annotated[str, Path(description="Target canonical id (ULID) to keep.")],
    body: MergeCanonicalIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_operator_id: Annotated[
        str | None, Header(alias=_OPERATOR_HEADER, include_in_schema=False)
    ] = None,
) -> MergeResultOut:
    operator = x_operator_id or _OPERATOR_FALLBACK
    source_id = body.source_canonical_product_id
    if source_id == canonical_product_id:
        raise ConflictError("A canonical product cannot be merged into itself.")

    target = await get_canonical(session, canonical_product_id)
    if target is None:
        raise NotFoundError(
            f"No target canonical product with id {canonical_product_id}.",
            instance=f"/v1/canonical-products/{canonical_product_id}/merge",
        )
    source = await get_canonical(session, source_id)
    if source is None:
        raise NotFoundError(
            f"No source canonical product with id {source_id}.",
            instance=f"/v1/canonical-products/{canonical_product_id}/merge",
        )

    now = utc_now()
    links = await links_for_canonical(session, source_id)
    for link in links:
        link.canonical_product_id = canonical_product_id
        link.decided_by = operator
        link.decided_at = now
        # Links already reflected downstream must re-emit so catalog repoints to the target.
        if link.status in _EMITTED_STATUSES:
            enqueue(
                session,
                link_confirmed_record(
                    link_id=link.link_id,
                    supplier_product_id=link.supplier_product_id,
                    canonical_product_id=canonical_product_id,
                    method="manual",
                    confidence=link.confidence,
                    decided_by=operator,
                    decided_at=now,
                ),
            )
    await delete_canonical(session, source)
    record_decision(
        session,
        action="merge",
        operator=operator,
        canonical_product_id=canonical_product_id,
        note=f"merged {source_id} into {canonical_product_id} ({len(links)} links)",
    )
    await session.commit()
    return MergeResultOut(
        target_canonical_product_id=canonical_product_id,
        source_canonical_product_id=source_id,
        moved_links=len(links),
    )
