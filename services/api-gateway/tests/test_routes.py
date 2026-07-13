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


async def test_confirm_link__forwards_operator_id_from_principal(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.MATCHING_CURATE) as c:
        await c.post("/v1/curation/links/01JSP/confirm", headers=auth)
    sent = backend.requests[-1]
    # The gateway sets the operator identity from the authenticated principal, not the client.
    assert sent.headers["x-operator-id"] == "agent:test"


async def test_reject_link__forwards_operator_id_from_principal(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.MATCHING_CURATE) as c:
        await c.post("/v1/curation/links/01JSP/reject", headers=auth)
    sent = backend.requests[-1]
    assert sent.headers["x-operator-id"] == "agent:test"


async def test_list_canonical_products__forwards_to_matching(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get(
            "/v1/canonical-products", params={"gtin": "04006381333931"}, headers=auth
        )
    assert resp.status_code == 200
    sent = backend.requests[-1]
    assert str(sent.url).startswith("http://matching.test/v1/canonical-products")
    assert sent.url.params["gtin"] == "04006381333931"


async def test_get_canonical_product__forwards_to_matching(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.CATALOG_READ) as c:
        await c.get("/v1/canonical-products/01JCANON", headers=auth)
    sent = backend.requests[-1]
    assert str(sent.url) == "http://matching.test/v1/canonical-products/01JCANON"


async def test_create_new__forwards_body_and_operator_id(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.MATCHING_CURATE) as c:
        resp = await c.post(
            "/v1/curation/links/01JSP/create-new",
            json={"title": "Acme Widget", "brand": "Acme", "gtin": None},
            headers=auth,
        )
    assert resp.status_code == 200
    sent = backend.requests[-1]
    assert sent.method == "POST"
    assert str(sent.url) == "http://matching.test/v1/curation/links/01JSP/create-new"
    assert sent.headers["x-operator-id"] == "agent:test"
    assert sent.read().decode().find("Acme Widget") != -1


async def test_create_new__requires_matching_curate_scope(
    client: ClientFactory, auth: Headers
) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.post(
            "/v1/curation/links/01JSP/create-new", json={"title": "x"}, headers=auth
        )
    assert resp.status_code == 403


async def test_sync_accounts__forwards_to_sync_orchestrator(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.json = [{"account_id": "01J", "status": "ok"}]
    async with client(S.SYNC_READ) as c:
        resp = await c.get("/v1/sync/accounts", headers=auth)
    assert resp.status_code == 200
    assert str(backend.requests[-1].url) == "http://sync-orchestrator.test/v1/sync/accounts"


async def test_sync_accounts__requires_sync_read_scope(
    client: ClientFactory, auth: Headers
) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/sync/accounts", headers=auth)
    assert resp.status_code == 403


async def test_trigger_sync__forwards_post(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.SYNC_READ) as c:
        await c.post("/v1/sync/accounts/01JACCT/trigger", headers=auth)
    sent = backend.requests[-1]
    assert sent.method == "POST"
    assert str(sent.url) == "http://sync-orchestrator.test/v1/sync/accounts/01JACCT/trigger"


async def test_stats__forwards_to_matching(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.json = {
        "pending_reviews": 3,
        "canonical_products": 10,
        "decisions_total": 5,
        "decisions_by_action": {"confirm": 4, "reject": 1},
    }
    async with client(S.MATCHING_CURATE) as c:
        resp = await c.get("/v1/curation/stats", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["pending_reviews"] == 3
    assert str(backend.requests[-1].url) == "http://matching.test/v1/curation/stats"


async def test_stats__requires_matching_curate_scope(client: ClientFactory, auth: Headers) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/curation/stats", headers=auth)
    assert resp.status_code == 403


async def test_decisions__forwards_to_matching_with_filter(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    backend.json = {"items": [{"decision_id": "01J", "action": "confirm"}], "next_cursor": None}
    async with client(S.MATCHING_CURATE) as c:
        resp = await c.get(
            "/v1/curation/decisions",
            params={"supplier_product_id": "01JSP", "limit": 10},
            headers=auth,
        )
    assert resp.status_code == 200
    sent = backend.requests[-1]
    assert str(sent.url).startswith("http://matching.test/v1/curation/decisions")
    assert sent.url.params["supplier_product_id"] == "01JSP"


async def test_decisions__requires_matching_curate_scope(
    client: ClientFactory, auth: Headers
) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/curation/decisions", headers=auth)
    assert resp.status_code == 403


async def test_merge__forwards_body_and_operator_id(
    client: ClientFactory, backend: Any, auth: Headers
) -> None:
    async with client(S.MATCHING_CURATE) as c:
        await c.post(
            "/v1/canonical-products/01JTARGET/merge",
            json={"source_canonical_product_id": "01JSOURCE"},
            headers=auth,
        )
    sent = backend.requests[-1]
    assert sent.method == "POST"
    assert str(sent.url) == "http://matching.test/v1/canonical-products/01JTARGET/merge"
    assert sent.headers["x-operator-id"] == "agent:test"
    assert sent.read().decode().find("01JSOURCE") != -1


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
