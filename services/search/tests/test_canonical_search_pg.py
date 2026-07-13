"""Canonical-product search on a real Postgres (testcontainers). Integration — Docker only."""

from __future__ import annotations

import pytest
from search.adapters.canonical_repository import (
    canonical_semantic_search,
    canonical_sparse_candidates,
    index_canonical_document,
)
from search.domain.embedding import HashingEmbedder, product_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.catalog_product_updated import CatalogProductUpdated

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


def _card(cid: str, title: str, *, brand: str | None = "ASUS") -> CatalogProductUpdated:
    return CatalogProductUpdated(
        schema_version=1,
        canonical_product_id=cid,
        title=title,
        brand=brand,
        gtin=None,
        status="confirmed",  # type: ignore[arg-type]
        supplier_product_ids=[],
        updated_at="2026-07-13T00:00:00Z",  # type: ignore[arg-type]
    )


async def test_canonical_semantic__pgvector_nearest_on_postgres(
    pg_session_factory: SessionFactory,
) -> None:
    embedder = HashingEmbedder()
    docs = {
        "01J00000000000000000000001": "ASUS TUF B850-PLUS WiFi motherboard",
        "01J00000000000000000000002": "Logitech MX Master wireless mouse",
    }
    async with pg_session_factory() as session, session.begin():
        for cid, title in docs.items():
            await index_canonical_document(
                session, _card(cid, title), embedding=embedder.embed(product_text(title, "ASUS"))
            )

    query = embedder.embed("asus b850 wifi motherboard")
    async with pg_session_factory() as session:
        hits = await canonical_semantic_search(session, query, limit=5)

    assert hits[0][0].canonical_product_id == "01J00000000000000000000001"


async def test_canonical_sparse__ranks_by_inner_product_on_postgres(
    pg_session_factory: SessionFactory,
) -> None:
    async with pg_session_factory() as session, session.begin():
        await index_canonical_document(
            session, _card("01J00000000000000000000001", "a"), sparse={10: 0.2, 20: 0.9}
        )
        await index_canonical_document(
            session, _card("01J00000000000000000000002", "b"), sparse={10: 0.9, 30: 0.1}
        )

    async with pg_session_factory() as session:
        hits = await canonical_sparse_candidates(session, {20: 1.0, 10: 0.1})

    assert [h.canonical_product_id for h in hits] == [
        "01J00000000000000000000001",
        "01J00000000000000000000002",
    ]
