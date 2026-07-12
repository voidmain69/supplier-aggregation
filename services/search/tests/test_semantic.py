"""Semantic search: ranking by embedding similarity (SQLite Python fallback) + API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from search.adapters.repository import semantic_search
from search.api.deps import get_session_factory
from search.domain.embedding import HashingEmbedder
from search.events.handlers import build_discovered_handler
from search.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _seed(factory: SessionFactory, events: list[dict[str, Any]]) -> None:
    handler = build_discovered_handler(factory)
    for event in events:
        await handler(event)


async def test_semantic_search__ranks_most_similar_first(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            discovered_event(
                supplier_product_id="01J00000000000000000000001",
                name="ASUS TUF B850-PLUS WiFi motherboard",
                brand="ASUS",
            ),
            discovered_event(
                supplier_product_id="01J00000000000000000000002",
                name="Logitech MX Master wireless mouse",
                brand="Logitech",
            ),
        ],
    )
    query = HashingEmbedder().embed("asus b850 wifi motherboard")

    async with sqlite_session_factory() as session:
        hits = await semantic_search(session, query, limit=5)

    assert hits[0][0].supplier_product_id == "01J00000000000000000000001"
    assert hits[0][1] > hits[1][1]  # the motherboard scores higher than the mouse


async def test_semantic_search__ignores_documents_without_embedding(
    sqlite_session_factory: SessionFactory,
) -> None:
    async with sqlite_session_factory() as session:
        hits = await semantic_search(session, HashingEmbedder().embed("anything"))
    assert hits == []


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_semantic_endpoint__returns_scored_hits(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        [discovered_event(supplier_product_id="01J00000000000000000000001", name="ASUS B850 WiFi")],
    )
    async with client:
        resp = await client.post("/v1/search/semantic", json={"query": "asus wifi board"})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["supplier_product_id"] == "01J00000000000000000000001"
    assert isinstance(body[0]["score"], float)


async def test_semantic_endpoint__empty_query_rejected_422(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/search/semantic", json={"query": ""})
    assert resp.status_code == 422
