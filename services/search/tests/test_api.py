from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from search.api.deps import get_session_factory
from search.events.handlers import build_discovered_handler
from search.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _seed(factory: SessionFactory, event: dict[str, Any]) -> None:
    await build_discovered_handler(factory)(event)


async def test_search__post_returns_matches(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        discovered_event(supplier_product_id="01J00000000000000000000001", name="ASUS TUF B850"),
    )
    async with client:
        resp = await client.post("/v1/search", json={"query": "asus b850"})
    assert resp.status_code == 200
    body = resp.json()
    assert [h["supplier_product_id"] for h in body["items"]] == ["01J00000000000000000000001"]


async def test_search__empty_query_rejected_422(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/search", json={"query": ""})
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_by_code(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        discovered_event(supplier_product_id="01J00000000000000000000001", external_code="U777"),
    )
    async with client:
        resp = await client.get("/v1/search/by-code/U777")
    assert resp.status_code == 200
    assert resp.json()[0]["external_code"] == "U777"


async def test_by_gtin__invalid_returns_empty(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.get("/v1/search/by-gtin/nope")
    assert resp.status_code == 200
    assert resp.json() == []
