from __future__ import annotations

from mcp_gateway import tools
from mcp_gateway.clients import CatalogClient, OfferClient

_PROD = "01J0000000000000000PROD1"


async def test_search_products__returns_items(catalog: CatalogClient) -> None:
    result = await tools.search_products(catalog, supplier="brain")
    assert result["items"][0]["supplier_product_id"] == _PROD


async def test_get_product__found_and_missing(catalog: CatalogClient) -> None:
    found = await tools.get_product(catalog, _PROD)
    assert found["found"] is True
    assert found["product"]["gtin"] == "04711387781609"

    missing = await tools.get_product(catalog, "nope")
    assert missing["found"] is False


async def test_get_offers__lists(offer: OfferClient) -> None:
    result = await tools.get_offers(offer, _PROD)
    assert result["items"][0]["price_uah"] == "9900.0000"


async def test_get_best_offer__found_and_missing(offer: OfferClient) -> None:
    best = await tools.get_best_offer(offer, _PROD)
    assert best["found"] is True
    assert best["offer"]["offer_id"] == "01J000000000000000OFFER1"

    missing = await tools.get_best_offer(offer, "nope")
    assert missing["found"] is False


async def test_get_product_with_best_offer__aggregates(
    catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.get_product_with_best_offer(catalog, offer, _PROD)
    assert result["found"] is True
    assert result["product"]["supplier_product_id"] == _PROD
    assert result["best_offer"]["currency"] == "USD"


async def test_get_product_with_best_offer__missing_product(
    catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.get_product_with_best_offer(catalog, offer, "nope")
    assert result["found"] is False


async def test_best_offer_for_canonical__cheapest_across_suppliers(
    catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.best_offer_for_canonical(catalog, offer, "01J0000000000000000CAN01")
    assert result["found"] is True
    assert result["suppliers_considered"] == 2
    # PROD2 (acme) at 9500 UAH beats PROD1 (brain) at 9900
    assert result["best_offer"]["offer_id"] == "01J000000000000000OFFER2"


async def test_best_offer_for_canonical__no_suppliers(
    catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.best_offer_for_canonical(catalog, offer, "unknown-canonical")
    assert result["found"] is False
