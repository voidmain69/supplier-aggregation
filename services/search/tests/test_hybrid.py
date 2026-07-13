"""Hybrid search endpoint: lexical+semantic fusion then rerank (SQLite + injected reranker)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from search.api.deps import get_reranker, get_session_factory, get_sparse_embedder
from search.events.handlers import build_discovered_handler
from search.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]

_MOUSE = "01J00000000000000000000001"
_BOARD = "01J00000000000000000000002"


async def _seed(factory: SessionFactory, events: list[dict[str, Any]]) -> None:
    handler = build_discovered_handler(factory)
    for event in events:
        await handler(event)


class _KeywordReranker:
    """Deterministic fake reranker: ranks docs containing the query's first token first."""

    def rerank(self, query: str, documents: Sequence[str]) -> list[tuple[int, float]]:
        token = query.split(maxsplit=1)[0].lower()
        scored = [(i, 1.0 if token in doc.lower() else 0.0) for i, doc in enumerate(documents)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored


class _FakeSparseEmbedder:
    """Stub sparse embedder; on SQLite sparse_candidates returns [], so it just proves wiring."""

    def embed_sparse(self, text: str) -> dict[int, float]:
        return {1: 1.0}


_KEYWORD_RERANKER = _KeywordReranker()
_FAKE_SPARSE_EMBEDDER = _FakeSparseEmbedder()


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    app.dependency_overrides[get_reranker] = lambda: _KEYWORD_RERANKER
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_hybrid__reranker_decides_final_order(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            discovered_event(
                supplier_product_id=_BOARD, name="ASUS B850 motherboard", brand="ASUS", gtin=None
            ),
            discovered_event(
                supplier_product_id=_MOUSE,
                name="Logitech wireless mouse",
                brand="Logitech",
                gtin=None,
            ),
        ],
    )
    async with client:
        resp = await client.post("/v1/search/hybrid", json={"query": "mouse wireless"})

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["supplier_product_id"] == _MOUSE  # reranker prefers the "mouse" doc
    assert {hit["supplier_product_id"] for hit in body} == {_MOUSE, _BOARD}
    assert isinstance(body[0]["score"], float)


async def test_hybrid__limit_caps_results(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            discovered_event(supplier_product_id=_MOUSE, name="wireless mouse", gtin=None),
            discovered_event(supplier_product_id=_BOARD, name="wireless keyboard", gtin=None),
        ],
    )
    async with client:
        resp = await client.post("/v1/search/hybrid", json={"query": "wireless", "limit": 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_hybrid__empty_query_rejected_422(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/search/hybrid", json={"query": ""})
    assert resp.status_code == 422


async def test_hybrid__configured_sparse_embedder_skipped_gracefully_on_sqlite(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    # With a sparse embedder wired, the route embeds the query but sparse_candidates returns []
    # on SQLite — results stay lexical+dense and nothing errors.
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    app.dependency_overrides[get_reranker] = lambda: _KEYWORD_RERANKER
    app.dependency_overrides[get_sparse_embedder] = lambda: _FAKE_SPARSE_EMBEDDER
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")

    await _seed(
        sqlite_session_factory,
        [
            discovered_event(supplier_product_id=_MOUSE, name="wireless mouse", gtin=None),
            discovered_event(supplier_product_id=_BOARD, name="ASUS motherboard", gtin=None),
        ],
    )
    async with client:
        resp = await client.post("/v1/search/hybrid", json={"query": "mouse wireless"})

    assert resp.status_code == 200
    assert {hit["supplier_product_id"] for hit in resp.json()} == {_MOUSE, _BOARD}
