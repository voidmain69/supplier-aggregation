"""Search index on a real Postgres (testcontainers). Integration — Docker only.

Guards the case-handling: Postgres LIKE is case-sensitive, so lexical search relies on both
the stored text and the query being lowercased. This proves a mixed-case query still matches.
"""

from __future__ import annotations

import pytest
from search.adapters.repository import find_by_gtin, index_document, search, semantic_search
from search.domain.embedding import HashingEmbedder, product_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

pytestmark = pytest.mark.integration

SessionFactory = async_sessionmaker[AsyncSession]


def _doc(spid: str, *, name: str, gtin: str | None = None) -> SupplierProductDiscovered:
    return SupplierProductDiscovered(
        schema_version=1,
        supplier_product_id=spid,
        supplier_code="brain",
        external_id="100463720",
        external_code="U100",
        articul="ART",
        gtin=gtin,
        raw_identifiers={},
        name=name,
        brand="ASUS",
        supplier_category_id=None,
        attributes={},
        content_hash="h",
        sync_job_id="01JSYNC",
    )


async def test_search__case_insensitive_on_postgres(pg_session_factory: SessionFactory) -> None:
    async with pg_session_factory() as session, session.begin():
        await index_document(session, _doc("01J00000000000000000000001", name="ASUS TUF B850"))

    async with pg_session_factory() as session:
        hits, _ = await search(session, "AsUs B850")  # mixed case query still matches
        by_gtin_empty = await find_by_gtin(session, "0000")

    assert [h.supplier_product_id for h in hits] == ["01J00000000000000000000001"]
    assert by_gtin_empty == []


async def test_semantic_search__pgvector_nearest_on_postgres(
    pg_session_factory: SessionFactory,
) -> None:
    embedder = HashingEmbedder()
    docs = {
        "01J00000000000000000000001": "ASUS TUF B850-PLUS WiFi motherboard",
        "01J00000000000000000000002": "Logitech MX Master wireless mouse",
    }
    async with pg_session_factory() as session, session.begin():
        for spid, name in docs.items():
            await index_document(
                session,
                _doc(spid, name=name),
                embedding=embedder.embed(product_text(name, "ASUS")),
            )

    query = embedder.embed("asus b850 wifi motherboard")
    async with pg_session_factory() as session:
        hits = await semantic_search(session, query, limit=5)

    assert hits[0][0].supplier_product_id == "01J00000000000000000000001"
    assert 0.0 <= hits[0][1] <= 1.0
