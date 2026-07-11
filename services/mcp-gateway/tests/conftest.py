from __future__ import annotations

from typing import Any

import httpx
import pytest
from mcp_gateway.clients import CatalogClient, OfferClient

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


class FakeBackends:
    """Fakes the catalog + offer HTTP APIs behind an httpx.MockTransport."""

    def __init__(self) -> None:
        self.known_product = _PRODUCT["supplier_product_id"]

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/supplier-products":
            return httpx.Response(200, json={"items": [_PRODUCT], "next_cursor": None})
        if path.startswith("/v1/supplier-products/"):
            pid = path.rsplit("/", 1)[-1]
            if pid == self.known_product:
                return httpx.Response(200, json=_PRODUCT)
            return httpx.Response(404, json={"type": "x/not-found", "status": 404})
        if path == "/v1/offers":
            return httpx.Response(200, json={"items": [_OFFER], "next_cursor": None})
        if path == "/v1/offers/best":
            pid = request.url.params.get("supplier_product_id")
            if pid == self.known_product:
                return httpx.Response(200, json=_OFFER)
            return httpx.Response(404, json={"type": "x/not-found", "status": 404})
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
def sample_product() -> dict[str, Any]:
    return dict(_PRODUCT)
