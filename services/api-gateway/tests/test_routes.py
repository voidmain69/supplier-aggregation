"""Proxying: the gateway forwards to the right service and relays the response."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from api_gateway.domain.auth import Scopes as S

ClientFactory = Callable[..., httpx.AsyncClient]
Headers = dict[str, str]


async def test_list_products__forwards_to_catalog_with_filters(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.json = {"items": [{"supplier_product_id": "01J"}], "next_cursor": None}
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products", params={"supplier": "brain", "limit": 10}, headers=auth)

    assert resp.status_code == 200
    assert resp.json()["items"][0]["supplier_product_id"] == "01J"
    sent = backend.requests[-1]
    assert str(sent.url).startswith("http://catalog.test/v1/supplier-products")
    assert sent.url.params["supplier"] == "brain"
    assert sent.url.params["limit"] == "10"
    assert "canonical_product_id" not in sent.url.params  # None params are dropped


async def test_best_offer__forwards_to_offer_service(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.OFFERS_READ) as c:
        await c.get("/v1/products/01JABC/best-offer", headers=auth)
    sent = backend.requests[-1]
    assert str(sent.url).startswith("http://offer.test/v1/offers/best")
    assert sent.url.params["supplier_product_id"] == "01JABC"


async def test_price_history__maps_from_alias(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.PRICES_READ) as c:
        await c.get(
            "/v1/offers/01JOFF/price-history",
            params={"from": "2026-07-01T00:00:00Z"},
            headers=auth,
        )
    sent = backend.requests[-1]
    assert str(sent.url).startswith("http://price-history.test/v1/price-history")
    assert sent.url.params["offer_id"] == "01JOFF"
    assert sent.url.params["from"] == "2026-07-01T00:00:00Z"


async def test_confirm_link__forwards_post_to_matching(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.MATCHING_CURATE) as c:
        await c.post("/v1/curation/links/01JSP/confirm", headers=auth)
    sent = backend.requests[-1]
    assert sent.method == "POST"
    assert str(sent.url) == "http://matching.test/v1/curation/links/01JSP/confirm"


async def test_downstream_404__is_relayed_as_problem_json(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.status = 404
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products/nope", headers=auth)
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_downstream_unreachable__is_502(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.raise_transport = True
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products", headers=auth)
    assert resp.status_code == 502
    assert resp.headers["content-type"].startswith("application/problem+json")
