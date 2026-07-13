"""Operator curation API: the review queue and confirm/reject decisions (AI-ready).

Confirming a candidate flips the link to ``confirmed`` and emits
``matching.link.confirmed`` (method ``manual``) via the outbox, closing the loop just like
the GTIN pass. Auth/scopes (``matching:curate``) come with the API gateway.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.repository import (
    create_canonical,
    find_canonical_by_gtin,
    get_canonical,
    get_link,
    list_pending_links,
)
from matching.api.deps import get_session
from matching.api.schemas import CreateCanonicalIn, CurationItemOut, LinkDecisionOut, Problem
from matching.events.mapping import link_confirmed_record
from sa_core.errors import ConflictError, NotFoundError
from sa_core.pagination import Page
from sa_core.time import utc_now

router = APIRouter(prefix="/v1/curation", tags=["curation"])

# The operator identity is set by the API gateway from the authenticated principal and passed
# as ``X-Operator-Id`` (a trusted, gateway-only header — matching is not publicly reachable).
# Direct calls without the gateway fall back to a generic label so the audit is never blank.
_OPERATOR_HEADER = "X-Operator-Id"
_OPERATOR_FALLBACK = "operator"
_ERRORS: dict[int | str, dict[str, object]] = {
    404: {"model": Problem, "description": "No such curation item."},
    409: {"model": Problem, "description": "Item already decided."},
}


@router.get(
    "/queue",
    operation_id="listCurationQueue",
    summary="List the matching curation queue",
    description=(
        "Supplier→canonical links awaiting an operator decision (status pending_review), "
        "oldest first. Cursor paginated. Confirm or reject each via the endpoints below."
    ),
    response_model=Page[CurationItemOut],
)
async def list_queue(
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=200, description="Max items per page (1-200, default 50).")
    ] = 50,
) -> Page[CurationItemOut]:
    rows, next_cursor = await list_pending_links(session, cursor=cursor, limit=limit)
    items = [
        CurationItemOut(
            supplier_product_id=r.supplier_product_id,
            canonical_product_id=r.canonical_product_id,
            method=r.method,
            confidence=r.confidence,
            status=r.status,
        )
        for r in rows
    ]
    return Page(items=items, next_cursor=next_cursor)


@router.post(
    "/links/{supplier_product_id}/confirm",
    operation_id="confirmLink",
    summary="Confirm a suggested match",
    description=(
        "Confirm the suggested canonical for a supplier product. Marks the link confirmed "
        "(and the canonical, if it was a draft) and emits matching.link.confirmed. "
        "Idempotent: confirming an already-confirmed link is a no-op."
    ),
    response_model=LinkDecisionOut,
    responses=_ERRORS,
)
async def confirm_link(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID) to confirm.")],
    session: Annotated[AsyncSession, Depends(get_session)],
    x_operator_id: Annotated[
        str | None, Header(alias=_OPERATOR_HEADER, include_in_schema=False)
    ] = None,
) -> LinkDecisionOut:
    operator = x_operator_id or _OPERATOR_FALLBACK
    link = await get_link(session, supplier_product_id)
    if link is None:
        raise NotFoundError(
            f"No curation item for supplier product {supplier_product_id}.",
            instance=f"/v1/curation/links/{supplier_product_id}/confirm",
        )
    if link.status == "rejected":
        raise ConflictError("This link was rejected and cannot be confirmed.")
    if link.status == "confirmed":
        return LinkDecisionOut(
            supplier_product_id=link.supplier_product_id,
            canonical_product_id=link.canonical_product_id,
            status=link.status,
        )

    link.status = "confirmed"
    link.decided_by = operator
    link.decided_at = utc_now()
    canonical = await get_canonical(session, link.canonical_product_id)
    if canonical is not None and canonical.status == "draft":
        canonical.status = "confirmed"
    enqueue(
        session,
        link_confirmed_record(
            link_id=link.link_id,
            supplier_product_id=link.supplier_product_id,
            canonical_product_id=link.canonical_product_id,
            method="manual",
            confidence=link.confidence,
            decided_by=operator,
            decided_at=link.decided_at,
        ),
    )
    await session.commit()
    return LinkDecisionOut(
        supplier_product_id=link.supplier_product_id,
        canonical_product_id=link.canonical_product_id,
        status=link.status,
    )


@router.post(
    "/links/{supplier_product_id}/reject",
    operation_id="rejectLink",
    summary="Reject a suggested match",
    description=(
        "Reject the suggested canonical for a supplier product. Idempotent: rejecting an "
        "already-rejected link is a no-op. A confirmed link cannot be rejected."
    ),
    response_model=LinkDecisionOut,
    responses=_ERRORS,
)
async def reject_link(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID) to reject.")],
    session: Annotated[AsyncSession, Depends(get_session)],
    x_operator_id: Annotated[
        str | None, Header(alias=_OPERATOR_HEADER, include_in_schema=False)
    ] = None,
) -> LinkDecisionOut:
    operator = x_operator_id or _OPERATOR_FALLBACK
    link = await get_link(session, supplier_product_id)
    if link is None:
        raise NotFoundError(
            f"No curation item for supplier product {supplier_product_id}.",
            instance=f"/v1/curation/links/{supplier_product_id}/reject",
        )
    if link.status == "confirmed":
        raise ConflictError("This link was confirmed and cannot be rejected.")
    if link.status != "rejected":
        link.status = "rejected"
        link.decided_by = operator
        link.decided_at = utc_now()
        await session.commit()
    return LinkDecisionOut(
        supplier_product_id=link.supplier_product_id,
        canonical_product_id=link.canonical_product_id,
        status=link.status,
    )


@router.post(
    "/links/{supplier_product_id}/create-new",
    operation_id="createNewCanonical",
    summary="Create a new canonical from a curation item",
    description=(
        "Reject the suggested candidate and instead create a brand-new canonical product from "
        "this supplier product, linking it confirmed. Use it when the suggestion is wrong and no "
        "existing canonical fits. Emits matching.link.confirmed for the new canonical."
    ),
    response_model=LinkDecisionOut,
    responses=_ERRORS,
)
async def create_new_canonical(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID).")],
    body: CreateCanonicalIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    x_operator_id: Annotated[
        str | None, Header(alias=_OPERATOR_HEADER, include_in_schema=False)
    ] = None,
) -> LinkDecisionOut:
    operator = x_operator_id or _OPERATOR_FALLBACK
    link = await get_link(session, supplier_product_id)
    if link is None:
        raise NotFoundError(
            f"No curation item for supplier product {supplier_product_id}.",
            instance=f"/v1/curation/links/{supplier_product_id}/create-new",
        )
    if link.status == "confirmed":
        raise ConflictError("This link is already confirmed; it cannot be re-created.")
    if body.gtin is not None and await find_canonical_by_gtin(session, body.gtin) is not None:
        raise ConflictError(
            f"A canonical product already carries GTIN {body.gtin}; confirm that match instead "
            "of creating a new product."
        )

    canonical = create_canonical(
        session, gtin=body.gtin, brand=body.brand, title=body.title, status="confirmed"
    )
    link.canonical_product_id = canonical.canonical_product_id
    link.method = "manual"
    link.confidence = 1.0
    link.status = "confirmed"
    link.decided_by = operator
    link.decided_at = utc_now()
    enqueue(
        session,
        link_confirmed_record(
            link_id=link.link_id,
            supplier_product_id=link.supplier_product_id,
            canonical_product_id=canonical.canonical_product_id,
            method="manual",
            confidence=1.0,
            decided_by=operator,
            decided_at=link.decided_at,
        ),
    )
    await session.commit()
    return LinkDecisionOut(
        supplier_product_id=link.supplier_product_id,
        canonical_product_id=link.canonical_product_id,
        status=link.status,
    )
