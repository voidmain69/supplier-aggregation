"""Task-oriented tool logic (independent of the MCP transport, so it is unit-testable).

Each function takes the HTTP clients and returns a plain dict the MCP layer hands back to
the agent. The gateway's value is task-oriented, aggregating tools — not a 1:1 proxy of
every endpoint.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from mcp_gateway.clients import CatalogClient, OfferClient, PriceHistoryClient


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
