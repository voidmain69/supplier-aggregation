from __future__ import annotations

from mcp_gateway import tools
from mcp_gateway.clients import CatalogClient, OfferClient, PriceHistoryClient, SearchClient

_PROD = "01J0000000000000000PROD1"
_OFFER_ID = "01J000000000000000OFFER1"


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


async def test_get_price_history__returns_time_series(
    price_history: PriceHistoryClient,
) -> None:
    result = await tools.get_price_history(price_history, _OFFER_ID)
    assert [p["price_uah"] for p in result["items"]] == ["9900.0000", "9500.0000"]


async def test_get_price_history__unknown_offer_is_empty(
    price_history: PriceHistoryClient,
) -> None:
    result = await tools.get_price_history(price_history, "nope")
    assert result["items"] == []


async def test_get_offer_price_stats__aggregates(price_history: PriceHistoryClient) -> None:
    stats = await tools.get_offer_price_stats(
        price_history, _OFFER_ID, from_="2026-07-01T00:00:00Z"
    )
    assert stats["count"] == 2
    assert stats["min_uah"] == "9500.0000"
    assert stats["last_uah"] == "9500.0000"


async def test_get_price_daily__returns_day_buckets(price_history: PriceHistoryClient) -> None:
    result = await tools.get_price_daily(price_history, _OFFER_ID)
    assert result["offer_id"] == _OFFER_ID
    assert [d["day"] for d in result["days"]] == ["2026-07-10", "2026-07-11"]
    assert result["days"][1]["min_uah"] == "9500.0000"


async def test_get_price_daily__unknown_offer_is_empty(
    price_history: PriceHistoryClient,
) -> None:
    result = await tools.get_price_daily(price_history, "nope")
    assert result["days"] == []


async def test_find_products__returns_scored_hits(search: SearchClient) -> None:
    result = await tools.find_products(search, "asus b850 motherboard")
    assert result["query"] == "asus b850 motherboard"
    assert result["hits"][0]["supplier_product_id"] == _PROD
    assert result["hits"][0]["score"] > 0


async def test_find_products__no_match_is_empty(search: SearchClient) -> None:
    result = await tools.find_products(search, "no such thing")
    assert result["hits"] == []


async def test_find_canonical_products__returns_canonical_hits(search: SearchClient) -> None:
    result = await tools.find_canonical_products(search, "asus b850")
    assert result["hits"][0]["canonical_product_id"] == "01J0000000000000000CAN01"


async def test_best_price_for_query__search_to_cheapest_offer(
    search: SearchClient, catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.best_price_for_query(search, catalog, offer, "asus b850")
    assert result["found"] is True
    assert result["matched_canonical"]["canonical_product_id"] == "01J0000000000000000CAN01"
    # PROD2 (acme) at 9500 UAH beats PROD1 (brain) at 9900 — cheapest across suppliers wins.
    assert result["best_offer"]["offer_id"] == "01J000000000000000OFFER2"


async def test_best_price_for_query__no_search_match(
    search: SearchClient, catalog: CatalogClient, offer: OfferClient
) -> None:
    result = await tools.best_price_for_query(search, catalog, offer, "no such thing")
    assert result["found"] is False
