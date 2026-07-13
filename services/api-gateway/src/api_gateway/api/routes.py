"""The single, authenticated ingress: one documented surface over the internal services.

Every operation requires a bearer token and a scope (see ``Requires scope`` in each
description) and is rate-limited per principal. Reads and curation writes are forwarded to
the owning service; downstream problem+json errors are relayed unchanged, so callers — human
or LLM — always get one consistent, self-describing contract.
"""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Path, Query, Response

from api_gateway.adapters.downstream import Downstream
from api_gateway.api.deps import get_downstream
from api_gateway.api.schemas import CreateCanonicalIn, MergeCanonicalIn, Problem
from api_gateway.api.security import require
from api_gateway.domain.auth import Principal, Scopes

router = APIRouter(prefix="/v1", tags=["gateway"])

# Auth/limit failures the gateway itself can raise on any operation (rendered as problem+json).
_GATEWAY_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": Problem, "description": "Missing or invalid bearer token."},
    403: {"model": Problem, "description": "The principal lacks the required scope."},
    429: {"model": Problem, "description": "Per-principal rate limit exceeded."},
    502: {"model": Problem, "description": "A downstream service was unreachable."},
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": Problem, "description": "The requested resource does not exist."}
}


def _relay(resp: httpx.Response) -> Response:
    """Return the downstream response verbatim (body + status + content-type)."""
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


# --------------------------------------------------------------------------- catalog
@router.get(
    "/products",
    operation_id="listProducts",
    summary="List supplier products",
    description=(
        "List supplier products from the catalog, optionally filtered by supplier or the "
        "canonical product they map to. Cursor-paginated. Requires scope `catalog:read`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def list_products(
    _: Annotated[Principal, Depends(require(Scopes.CATALOG_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    supplier: Annotated[
        str | None, Query(description="Filter by supplier code, e.g. `brain`.")
    ] = None,
    canonical_product_id: Annotated[
        str | None, Query(description="Filter to products mapped to this canonical id (ULID).")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max items per page (1-200).")] = 50,
) -> Response:
    resp = await downstream.request(
        "catalog",
        "GET",
        "/v1/supplier-products",
        params={
            "supplier": supplier,
            "canonical_product_id": canonical_product_id,
            "cursor": cursor,
            "limit": limit,
        },
    )
    return _relay(resp)


@router.get(
    "/products/{supplier_product_id}",
    operation_id="getProduct",
    summary="Get one supplier product",
    description=(
        "Fetch a single supplier product by its id, including the canonical product it maps "
        "to (if matched). Requires scope `catalog:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def get_product(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID).")],
    _: Annotated[Principal, Depends(require(Scopes.CATALOG_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "catalog", "GET", f"/v1/supplier-products/{supplier_product_id}"
    )
    return _relay(resp)


# ----------------------------------------------------------------------------- offers
@router.get(
    "/products/{supplier_product_id}/offers",
    operation_id="listProductOffers",
    summary="List offers for a product",
    description=(
        "List every supplier-account offer (price and availability) for a supplier product. "
        "Cursor-paginated. Requires scope `offers:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def list_product_offers(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID).")],
    _: Annotated[Principal, Depends(require(Scopes.OFFERS_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max items per page (1-200).")] = 50,
) -> Response:
    resp = await downstream.request(
        "offer",
        "GET",
        "/v1/offers",
        params={"supplier_product_id": supplier_product_id, "cursor": cursor, "limit": limit},
    )
    return _relay(resp)


@router.get(
    "/products/{supplier_product_id}/best-offer",
    operation_id="getBestOffer",
    summary="Get the cheapest offer for a product",
    description=(
        "Return the cheapest current offer (by UAH price) across all supplier accounts for a "
        "supplier product. Requires scope `offers:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def get_best_offer(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID).")],
    _: Annotated[Principal, Depends(require(Scopes.OFFERS_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "offer", "GET", "/v1/offers/best", params={"supplier_product_id": supplier_product_id}
    )
    return _relay(resp)


# ---------------------------------------------------------------------- price history
@router.get(
    "/offers/{offer_id}/price-history",
    operation_id="getOfferPriceHistory",
    summary="Get an offer's price history",
    description=(
        "Return the observed price points for one offer over a time range, oldest first. "
        "Cursor-paginated. Requires scope `prices:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def get_offer_price_history(
    offer_id: Annotated[str, Path(description="Offer id (ULID) to fetch history for.")],
    _: Annotated[Principal, Depends(require(Scopes.PRICES_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    from_: Annotated[
        str | None,
        Query(alias="from", description="Start of range, inclusive (ISO 8601 UTC)."),
    ] = None,
    to: Annotated[str | None, Query(description="End of range, inclusive (ISO 8601 UTC).")] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max points per page (1-500).")] = 100,
) -> Response:
    resp = await downstream.request(
        "price_history",
        "GET",
        "/v1/price-history",
        params={"offer_id": offer_id, "from": from_, "to": to, "cursor": cursor, "limit": limit},
    )
    return _relay(resp)


@router.get(
    "/offers/{offer_id}/price-history/stats",
    operation_id="getOfferPriceStats",
    summary="Get an offer's price statistics",
    description=(
        "Return aggregate UAH-price statistics (min/max/avg/last/count) for one offer over a "
        "time range. Requires scope `prices:read`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def get_offer_price_stats(
    offer_id: Annotated[str, Path(description="Offer id (ULID) to compute statistics for.")],
    _: Annotated[Principal, Depends(require(Scopes.PRICES_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    from_: Annotated[
        str | None,
        Query(alias="from", description="Start of range, inclusive (ISO 8601 UTC)."),
    ] = None,
    to: Annotated[str | None, Query(description="End of range, inclusive (ISO 8601 UTC).")] = None,
) -> Response:
    resp = await downstream.request(
        "price_history",
        "GET",
        "/v1/price-history/stats",
        params={"offer_id": offer_id, "from": from_, "to": to},
    )
    return _relay(resp)


# ----------------------------------------------------------------- canonical products
@router.get(
    "/canonical-products",
    operation_id="listCanonicalProducts",
    summary="List canonical products",
    description=(
        "List canonical (platform) products, optionally filtered by normalized GTIN-14. "
        "Cursor-paginated. Use it to resolve the canonical product a match suggestion points "
        "at, or to browse the confirmed catalog. Requires scope `catalog:read`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def list_canonical_products(
    _: Annotated[Principal, Depends(require(Scopes.CATALOG_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    gtin: Annotated[
        str | None, Query(description="Filter by normalized GTIN-14 (14 digits).")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max items per page (1-200).")] = 50,
) -> Response:
    resp = await downstream.request(
        "matching",
        "GET",
        "/v1/canonical-products",
        params={"gtin": gtin, "cursor": cursor, "limit": limit},
    )
    return _relay(resp)


@router.get(
    "/canonical-products/{canonical_product_id}",
    operation_id="getCanonicalProduct",
    summary="Get one canonical product",
    description=(
        "Fetch a single canonical product by its internal canonical_product_id (ULID). Use it "
        "to render the candidate side of a match review. Requires scope `catalog:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def get_canonical_product(
    canonical_product_id: Annotated[str, Path(description="Canonical product id (ULID).")],
    _: Annotated[Principal, Depends(require(Scopes.CATALOG_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "matching", "GET", f"/v1/canonical-products/{canonical_product_id}"
    )
    return _relay(resp)


@router.post(
    "/canonical-products/{canonical_product_id}/merge",
    operation_id="mergeCanonicalProducts",
    summary="Merge one canonical product into another",
    description=(
        "Fold a source canonical into this (target) one: its supplier-product links move to the "
        "target and the source is removed. Use it to deduplicate canonical products. Requires "
        "scope `matching:curate`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def merge_canonical_products(
    canonical_product_id: Annotated[str, Path(description="Target canonical id (ULID) to keep.")],
    body: MergeCanonicalIn,
    principal: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "matching",
        "POST",
        f"/v1/canonical-products/{canonical_product_id}/merge",
        json=body.model_dump(),
        headers={"X-Operator-Id": principal.subject},
    )
    return _relay(resp)


# --------------------------------------------------------------------------- curation
@router.get(
    "/curation/stats",
    operation_id="getCurationStats",
    summary="Curation stats for the operator dashboard",
    description=(
        "Aggregate counts for the operator dashboard: queue depth, total canonical products, and "
        "decisions by action. Requires scope `matching:curate`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def get_curation_stats(
    _: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    return _relay(await downstream.request("matching", "GET", "/v1/curation/stats"))


@router.get(
    "/curation/queue",
    operation_id="getCurationQueue",
    summary="List the matching curation queue",
    description=(
        "List supplier→canonical link suggestions awaiting an operator decision, oldest first. "
        "Cursor-paginated. Requires scope `matching:curate`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def get_curation_queue(
    _: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max items per page (1-200).")] = 50,
) -> Response:
    resp = await downstream.request(
        "matching", "GET", "/v1/curation/queue", params={"cursor": cursor, "limit": limit}
    )
    return _relay(resp)


@router.get(
    "/curation/decisions",
    operation_id="getCurationDecisions",
    summary="List the curation decision journal",
    description=(
        "Append-only audit log of curation decisions (confirm / reject / create-new / merge), "
        "newest first. Optionally filter to one supplier product's history. Cursor-paginated. "
        "Requires scope `matching:curate`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def get_curation_decisions(
    _: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
    supplier_product_id: Annotated[
        str | None, Query(description="Filter to one supplier product's decision history.")
    ] = None,
    cursor: Annotated[
        str | None, Query(description="Opaque cursor from a previous response's next_cursor.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max items per page (1-200).")] = 50,
) -> Response:
    resp = await downstream.request(
        "matching",
        "GET",
        "/v1/curation/decisions",
        params={
            "supplier_product_id": supplier_product_id,
            "cursor": cursor,
            "limit": limit,
        },
    )
    return _relay(resp)


@router.post(
    "/curation/links/{supplier_product_id}/confirm",
    operation_id="confirmCurationLink",
    summary="Confirm a suggested match",
    description=(
        "Confirm the suggested canonical for a supplier product; emits matching.link.confirmed "
        "downstream. Idempotent. Requires scope `matching:curate`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def confirm_curation_link(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID) to confirm.")],
    principal: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "matching",
        "POST",
        f"/v1/curation/links/{supplier_product_id}/confirm",
        headers={"X-Operator-Id": principal.subject},
    )
    return _relay(resp)


@router.post(
    "/curation/links/{supplier_product_id}/reject",
    operation_id="rejectCurationLink",
    summary="Reject a suggested match",
    description=(
        "Reject the suggested canonical for a supplier product. Idempotent. Requires scope "
        "`matching:curate`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def reject_curation_link(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID) to reject.")],
    principal: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "matching",
        "POST",
        f"/v1/curation/links/{supplier_product_id}/reject",
        headers={"X-Operator-Id": principal.subject},
    )
    return _relay(resp)


@router.post(
    "/curation/links/{supplier_product_id}/create-new",
    operation_id="createNewCanonical",
    summary="Create a new canonical from a curation item",
    description=(
        "Reject the suggested candidate and create a brand-new canonical product from this "
        "supplier product, linking it confirmed. Use it when the suggestion is wrong and no "
        "existing canonical fits. Requires scope `matching:curate`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def create_new_canonical(
    supplier_product_id: Annotated[str, Path(description="Supplier product id (ULID).")],
    body: CreateCanonicalIn,
    principal: Annotated[Principal, Depends(require(Scopes.MATCHING_CURATE))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    resp = await downstream.request(
        "matching",
        "POST",
        f"/v1/curation/links/{supplier_product_id}/create-new",
        json=body.model_dump(),
        headers={"X-Operator-Id": principal.subject},
    )
    return _relay(resp)


# ------------------------------------------------------------------------------ sync
@router.get(
    "/sync/accounts",
    operation_id="getSyncAccounts",
    summary="List sync status per account",
    description=(
        "Every scheduled account and its sync health (last requested, next due, status). "
        "Operational fields only — no credentials or financial terms. Requires scope `sync:read`."
    ),
    responses=_GATEWAY_ERRORS,
)
async def get_sync_accounts(
    _: Annotated[Principal, Depends(require(Scopes.SYNC_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    return _relay(await downstream.request("sync_orchestrator", "GET", "/v1/sync/accounts"))


@router.post(
    "/sync/accounts/{account_id}/trigger",
    operation_id="triggerSync",
    summary="Request a sync now",
    description=(
        "Manually request a sync for an account — emits sync.job.requested so its connector "
        "fetches fresh data immediately. Requires scope `sync:read`."
    ),
    responses={**_GATEWAY_ERRORS, **_NOT_FOUND},
)
async def trigger_sync(
    account_id: Annotated[str, Path(description="Account id (ULID) to sync now.")],
    _: Annotated[Principal, Depends(require(Scopes.SYNC_READ))],
    downstream: Annotated[Downstream, Depends(get_downstream)],
) -> Response:
    return _relay(
        await downstream.request(
            "sync_orchestrator", "POST", f"/v1/sync/accounts/{account_id}/trigger"
        )
    )
