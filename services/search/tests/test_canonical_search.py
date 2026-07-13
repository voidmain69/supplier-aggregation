"""Canonical-product search: index from catalog.product.updated + hybrid endpoint (SQLite)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from search.adapters.canonical_repository import canonical_semantic_search
from search.api.deps import get_reranker, get_session_factory
from search.domain.embedding import HashingEmbedder
from search.events.handlers import build_canonical_updated_handler
from search.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_core.events import make_cloud_event

SessionFactory = async_sessionmaker[AsyncSession]
_C1 = "01J0000000000000000CANON1"
_C2 = "01J0000000000000000CANON2"
_DATASCHEMA = "https://contracts.sa.internal/events/catalog.product.updated.json"


def _canonical_event(
    *, canonical_product_id: str, title: str, brand: str | None = None
) -> dict[str, Any]:
    return make_cloud_event(
        type="catalog.product.updated",
        source="//sa/catalog",
        subject=canonical_product_id,
        dataschema=_DATASCHEMA,
        data={
            "schema_version": 1,
            "canonical_product_id": canonical_product_id,
            "title": title,
            "brand": brand,
            "gtin": None,
            "status": "confirmed",
            "supplier_product_ids": [],
            "updated_at": "2026-07-13T00:00:00Z",
        },
    )


class _KeywordReranker:
    def rerank(self, query: str, documents: Sequence[str]) -> list[tuple[int, float]]:
        token = query.split(maxsplit=1)[0].lower()
        scored = [(i, 1.0 if token in doc.lower() else 0.0) for i, doc in enumerate(documents)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored


_KEYWORD_RERANKER = _KeywordReranker()


async def _seed(factory: SessionFactory, events: list[dict[str, Any]]) -> None:
    handler = build_canonical_updated_handler(factory)
    for event in events:
        await handler(event)


async def test_canonical_updated_handler__indexes_and_semantic_ranks(
    sqlite_session_factory: SessionFactory,
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            _canonical_event(canonical_product_id=_C1, title="ASUS B850 motherboard", brand="ASUS"),
            _canonical_event(
                canonical_product_id=_C2, title="Logitech wireless mouse", brand="Logitech"
            ),
        ],
    )
    query = HashingEmbedder().embed("asus b850 motherboard")
    async with sqlite_session_factory() as session:
        hits = await canonical_semantic_search(session, query, limit=5)

    assert hits[0][0].canonical_product_id == _C1


async def test_canonical_updated_handler__idempotent(
    sqlite_session_factory: SessionFactory,
) -> None:
    event = _canonical_event(canonical_product_id=_C1, title="thing")
    handler = build_canonical_updated_handler(sqlite_session_factory)
    await handler(event)
    await handler(event)  # redelivery -> no error, still one document

    async with sqlite_session_factory() as session:
        hits = await canonical_semantic_search(session, HashingEmbedder().embed("thing"))
    assert [h[0].canonical_product_id for h in hits] == [_C1]


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    app.dependency_overrides[get_reranker] = lambda: _KEYWORD_RERANKER
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_canonical_endpoint__returns_canonical_hits(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(
        sqlite_session_factory,
        [
            _canonical_event(canonical_product_id=_C1, title="ASUS B850 motherboard"),
            _canonical_event(canonical_product_id=_C2, title="Logitech wireless mouse"),
        ],
    )
    async with client:
        resp = await client.post("/v1/search/canonical", json={"query": "mouse wireless"})

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["canonical_product_id"] == _C2  # reranker prefers the "mouse" doc
    assert set(body[0]) >= {"canonical_product_id", "title", "score"}


async def test_canonical_endpoint__empty_query_rejected_422(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/search/canonical", json={"query": ""})
    assert resp.status_code == 422
