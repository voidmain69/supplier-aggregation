"""Operator curation API: the review queue and confirm/reject decisions (AI-ready).

Confirming a candidate flips the link to ``confirmed`` and emits
``matching.link.confirmed`` (method ``manual``) via the outbox, closing the loop just like
the GTIN pass. Auth/scopes (``matching:curate``) come with the API gateway.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sa_persistence.outbox import enqueue
from sqlalchemy.ext.asyncio import AsyncSession

from matching.adapters.repository import get_canonical, get_link, list_pending_links
from matching.api.deps import get_session
from matching.api.schemas import CurationItemOut, LinkDecisionOut, Problem
from matching.events.mapping import link_confirmed_record
from sa_core.errors import ConflictError, NotFoundError
from sa_core.pagination import Page
from sa_core.time import utc_now

router = APIRouter(prefix="/v1/curation", tags=["curation"])

_OPERATOR = "operator"  # operator identity comes from the API gateway (auth) — a follow-up
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
) -> LinkDecisionOut:
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
    link.decided_by = _OPERATOR
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
            decided_by=_OPERATOR,
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
) -> LinkDecisionOut:
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
        link.decided_by = _OPERATOR
        link.decided_at = utc_now()
        await session.commit()
    return LinkDecisionOut(
        supplier_product_id=link.supplier_product_id,
        canonical_product_id=link.canonical_product_id,
        status=link.status,
    )
