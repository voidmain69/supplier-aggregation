"""Task-oriented tool logic (independent of the MCP transport, so it is unit-testable).

Each function takes the HTTP clients and returns a plain dict the MCP layer hands back to
the agent. The gateway's value is task-oriented, aggregating tools — not a 1:1 proxy of
every endpoint.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from mcp_gateway.clients import CatalogClient, OfferClient, PriceHistoryClient, SearchClient


def _uah(offer: dict[str, Any]) -> Decimal | None:
    value = offer.get("price_uah")
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


async def search_products(
    catalog: CatalogClient,
    *,
    supplier: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search/browse supplier products, optionally filtered by supplier; cursor-paginated."""
    return await catalog.list_products(supplier=supplier, cursor=cursor, limit=limit)


async def get_product(catalog: CatalogClient, supplier_product_id: str) -> dict[str, Any]:
    """Fetch one supplier product, or a not-found marker."""
    product = await catalog.get_product(supplier_product_id)
    if product is None:
        return {"found": False, "supplier_product_id": supplier_product_id}
    return {"found": True, "product": product}


async def get_offers(offer: OfferClient, supplier_product_id: str) -> dict[str, Any]:
    """List all offers for a product across suppliers/accounts."""
    return await offer.list_offers(supplier_product_id)


async def get_best_offer(offer: OfferClient, supplier_product_id: str) -> dict[str, Any]:
    """Cheapest offer (lowest UAH price) for a product, or a not-found marker."""
    best = await offer.best_offer(supplier_product_id)
    if best is None:
        return {"found": False, "supplier_product_id": supplier_product_id}
    return {"found": True, "offer": best}


async def get_price_history(
    price_history: PriceHistoryClient,
    offer_id: str,
    *,
    from_: str | None = None,
    to: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """Time series of observed prices for one offer over a date range; cursor-paginated."""
    return await price_history.price_history(
        offer_id, from_=from_, to=to, cursor=cursor, limit=limit
    )


async def get_offer_price_stats(
    price_history: PriceHistoryClient,
    offer_id: str,
    *,
    from_: str | None = None,
    to: str | None = None,
) -> dict[str, Any]:
    """Aggregate UAH-price statistics (min/max/avg/last/count) for one offer over a range."""
    return await price_history.price_stats(offer_id, from_=from_, to=to)


async def get_product_with_best_offer(
    catalog: CatalogClient, offer: OfferClient, supplier_product_id: str
) -> dict[str, Any]:
    """Aggregate: the product plus its cheapest offer in one call (the gateway's value-add)."""
    product = await catalog.get_product(supplier_product_id)
    if product is None:
        return {"found": False, "supplier_product_id": supplier_product_id}
    best = await offer.best_offer(supplier_product_id)
    return {"found": True, "product": product, "best_offer": best}


async def find_products(search: SearchClient, query: str, *, limit: int = 20) -> dict[str, Any]:
    """Free-text hybrid search over supplier products; returns scored hits."""
    hits = await search.hybrid(query, limit=limit)
    return {"query": query, "hits": hits}


async def find_canonical_products(
    search: SearchClient, query: str, *, limit: int = 20
) -> dict[str, Any]:
    """Free-text hybrid search over canonical (platform) products; one hit per product."""
    hits = await search.canonical(query, limit=limit)
    return {"query": query, "hits": hits}


async def get_price_daily(
    price_history: PriceHistoryClient,
    offer_id: str,
    *,
    from_: str | None = None,
    to: str | None = None,
) -> dict[str, Any]:
    """Per-day price buckets (count/min/max/avg/last in UAH) for one offer."""
    days = await price_history.price_daily(offer_id, from_=from_, to=to)
    return {"offer_id": offer_id, "days": days}


async def best_price_for_query(
    search: SearchClient, catalog: CatalogClient, offer: OfferClient, query: str
) -> dict[str, Any]:
    """Aggregate: free-text query -> best canonical match -> cheapest offer anywhere.

    Searches canonical products, takes the top hit, and resolves its cheapest offer across
    all suppliers and accounts — the "what would this cost me" one-shot.
    """
    hits = await search.canonical(query, limit=1)
    if not hits:
        return {"found": False, "query": query}
    top = hits[0]
    result = await best_offer_for_canonical(catalog, offer, top["canonical_product_id"])
    return {**result, "query": query, "matched_canonical": top}


async def best_offer_for_canonical(
    catalog: CatalogClient, offer: OfferClient, canonical_product_id: str
) -> dict[str, Any]:
    """Cheapest offer for a canonical product across ALL suppliers and accounts.

    Resolves the canonical product to its supplier products (catalog), takes each one's
    cheapest offer (offer), and returns the overall cheapest by UAH price.
    """
    page = await catalog.list_products(canonical_product_id=canonical_product_id, limit=100)
    supplier_products = page.get("items", [])
    if not supplier_products:
        return {"found": False, "canonical_product_id": canonical_product_id}

    best: dict[str, Any] | None = None
    best_uah: Decimal | None = None
    for product in supplier_products:
        candidate = await offer.best_offer(product["supplier_product_id"])
        price = _uah(candidate) if candidate is not None else None
        if price is not None and (best_uah is None or price < best_uah):
            best, best_uah = candidate, price

    if best is None:
        return {"found": False, "canonical_product_id": canonical_product_id}
    return {
        "found": True,
        "canonical_product_id": canonical_product_id,
        "suppliers_considered": len(supplier_products),
        "best_offer": best,
    }
