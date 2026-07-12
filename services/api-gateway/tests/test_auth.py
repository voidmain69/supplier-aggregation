"""Authentication + authorization at the gateway boundary."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from api_gateway.domain.auth import Principal, StaticPrincipalStore, hash_token
from api_gateway.domain.auth import Scopes as S

ClientFactory = Callable[..., httpx.AsyncClient]
Headers = dict[str, str]


def test_hash_token__is_deterministic_and_not_the_raw_token() -> None:
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != "abc"
    assert len(hash_token("abc")) == 64  # sha256 hex


def test_static_store__resolves_only_known_hashes() -> None:
    p = Principal(subject="agent:x", scopes=frozenset({S.CATALOG_READ}))
    store = StaticPrincipalStore({hash_token("t"): p})
    assert store.resolve(hash_token("t")) is p
    assert store.resolve(hash_token("other")) is None


async def test_request__without_token_is_401(client: ClientFactory) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_request__unknown_token_is_401(client: ClientFactory) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


async def test_request__missing_scope_is_403(client: ClientFactory, auth: Headers) -> None:
    async with client(S.OFFERS_READ) as c:  # has offers, not catalog
        resp = await c.get("/v1/products", headers=auth)
    assert resp.status_code == 403
    assert "catalog:read" in resp.json()["detail"]


async def test_request__with_scope_is_allowed(client: ClientFactory, auth: Headers) -> None:
    async with client(S.CATALOG_READ) as c:
        resp = await c.get("/v1/products", headers=auth)
    assert resp.status_code == 200


@pytest.mark.parametrize("burst", [1])
async def test_request__rate_limited_is_429(
    client: ClientFactory, auth: Headers, burst: int
) -> None:
    async with client(S.CATALOG_READ, rate_per_second=0.0, burst=burst) as c:
        first = await c.get("/v1/products", headers=auth)
        second = await c.get("/v1/products", headers=auth)
    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers
