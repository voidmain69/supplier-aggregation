from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from mcp_gateway.clients import CatalogClient, OfferClient, PriceHistoryClient, SearchClient

_KNOWN_OFFER = "01J000000000000000OFFER1"
_PRICE_POINTS = [
    {"offer_id": _KNOWN_OFFER, "ts": "2026-07-10T10:00:00+00:00", "price_uah": "9900.0000"},
    {"offer_id": _KNOWN_OFFER, "ts": "2026-07-11T10:00:00+00:00", "price_uah": "9500.0000"},
]
_PRICE_STATS = {
    "offer_id": _KNOWN_OFFER,
    "count": 2,
    "min_uah": "9500.0000",
    "max_uah": "9900.0000",
    "avg_uah": "9700.0000",
    "last_uah": "9500.0000",
    "last_ts": "2026-07-11T10:00:00+00:00",
}

_PRODUCT = {
    "supplier_product_id": "01J0000000000000000PROD1",
    "supplier_code": "brain",
    "external_id": "100463720",
    "gtin": "04711387781609",
    "name": "ASUS TUF GAMING B850-PLUS WIFI",
}
_OFFER = {
    "offer_id": "01J000000000000000OFFER1",
    "supplier_account_id": "01J0000000000000000ACCT1",
    "supplier_product_id": "01J0000000000000000PROD1",
    "price": "222.2200",
    "currency": "USD",
    "price_uah": "9900.0000",
}
_CANONICAL = "01J0000000000000000CAN01"
_DAILY = [
    {
        "day": "2026-07-10",
        "count": 1,
        "min_uah": "9900.0000",
        "max_uah": "9900.0000",
        "avg_uah": "9900.0000",
        "last_uah": "9900.0000",
    },
    {
        "day": "2026-07-11",
        "count": 1,
        "min_uah": "9500.0000",
        "max_uah": "9500.0000",
        "avg_uah": "9500.0000",
        "last_uah": "9500.0000",
    },
]
_SEARCH_HIT = {
    "supplier_product_id": "01J0000000000000000PROD1",
    "supplier_code": "brain",
    "name": "ASUS TUF GAMING B850-PLUS WIFI",
    "brand": "ASUS",
    "gtin": "04711387781609",
    "score": 0.93,
}
_CANONICAL_HIT = {
    "canonical_product_id": _CANONICAL,
    "title": "ASUS TUF GAMING B850-PLUS WIFI",
    "brand": "ASUS",
    "gtin": "04711387781609",
    "score": 0.91,
}
_PRODUCT2 = {**_PRODUCT, "supplier_product_id": "01J0000000000000000PROD2", "supplier_code": "acme"}
_OFFER2 = {
    **_OFFER,
    "offer_id": "01J000000000000000OFFER2",
    "supplier_product_id": "01J0000000000000000PROD2",
    "price_uah": "9500.0000",  # cheaper than PROD1's 9900
}


class FakeBackends:
    """Fakes the catalog + offer HTTP APIs behind an httpx.MockTransport."""

    def __init__(self) -> None:
        self.known_product = _PRODUCT["supplier_product_id"]
        self.known_canonical = _CANONICAL

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/supplier-products":
            canonical = request.url.params.get("canonical_product_id")
            if canonical == _CANONICAL:
                items = [_PRODUCT, _PRODUCT2]  # two suppliers of the same canonical
            elif canonical is not None:
                items = []  # unknown canonical -> no supplier products
            else:
                items = [_PRODUCT]
            return httpx.Response(200, json={"items": items, "next_cursor": None})
        if path.startswith("/v1/supplier-products/"):
            pid = path.rsplit("/", 1)[-1]
            if pid == self.known_product:
                return httpx.Response(200, json=_PRODUCT)
            return httpx.Response(404, json={"type": "x/not-found", "status": 404})
        if path == "/v1/offers":
            return httpx.Response(200, json={"items": [_OFFER], "next_cursor": None})
        if path == "/v1/offers/best":
            pid = request.url.params.get("supplier_product_id")
            if pid == _PRODUCT["supplier_product_id"]:
                return httpx.Response(200, json=_OFFER)
            if pid == _PRODUCT2["supplier_product_id"]:
                return httpx.Response(200, json=_OFFER2)
            return httpx.Response(404, json={"type": "x/not-found", "status": 404})
        if path == "/v1/price-history/stats":
            oid = request.url.params.get("offer_id")
            stats = _PRICE_STATS if oid == _KNOWN_OFFER else {"offer_id": oid, "count": 0}
            return httpx.Response(200, json=stats)
        if path == "/v1/price-history/daily":
            oid = request.url.params.get("offer_id")
            return httpx.Response(200, json=_DAILY if oid == _KNOWN_OFFER else [])
        if path == "/v1/price-history":
            oid = request.url.params.get("offer_id")
            items = _PRICE_POINTS if oid == _KNOWN_OFFER else []
            return httpx.Response(200, json={"items": items, "next_cursor": None})
        if path == "/v1/search/hybrid":
            body = json.loads(request.content)
            hits = [_SEARCH_HIT] if "asus" in body["query"].lower() else []
            return httpx.Response(200, json=hits[: body.get("limit", 20)])
        if path == "/v1/search/canonical":
            body = json.loads(request.content)
            hits = [_CANONICAL_HIT] if "asus" in body["query"].lower() else []
            return httpx.Response(200, json=hits[: body.get("limit", 20)])
        return httpx.Response(404, json={"type": "x/not-found", "status": 404})


@pytest.fixture
def backends() -> FakeBackends:
    return FakeBackends()


@pytest.fixture
def http(backends: FakeBackends) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(backends.handler))


@pytest.fixture
def catalog(http: httpx.AsyncClient) -> CatalogClient:
    return CatalogClient("http://catalog", http)


@pytest.fixture
def offer(http: httpx.AsyncClient) -> OfferClient:
    return OfferClient("http://offer", http)


@pytest.fixture
def price_history(http: httpx.AsyncClient) -> PriceHistoryClient:
    return PriceHistoryClient("http://price-history", http)


@pytest.fixture
def search(http: httpx.AsyncClient) -> SearchClient:
    return SearchClient("http://search", http)


@pytest.fixture
def sample_product() -> dict[str, Any]:
    return dict(_PRODUCT)
