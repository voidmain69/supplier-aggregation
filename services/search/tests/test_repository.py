from __future__ import annotations

from collections.abc import Sequence

from search.adapters.models import SearchDocumentRow
from search.adapters.repository import (
    find_by_articul,
    find_by_code,
    find_by_gtin,
    index_document,
    search,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

SessionFactory = async_sessionmaker[AsyncSession]


def _doc(
    spid: str,
    *,
    name: str = "ASUS TUF Gaming B850-PLUS WiFi",
    brand: str | None = "ASUS",
    articul: str | None = "TUF-B850",
    external_code: str | None = "U100",
    gtin: str | None = None,
) -> SupplierProductDiscovered:
    return SupplierProductDiscovered(
        schema_version=1,
        supplier_product_id=spid,
        supplier_code="brain",
        external_id="100463720",
        external_code=external_code,
        articul=articul,
        gtin=gtin,
        raw_identifiers={},
        name=name,
        brand=brand,
        supplier_category_id=None,
        attributes={},
        content_hash="h",
        sync_job_id="01JSYNC",
    )


async def _index(factory: SessionFactory, docs: Sequence[SupplierProductDiscovered]) -> None:
    async with factory() as session, session.begin():
        for doc in docs:
            await index_document(session, doc)


async def test_search__all_tokens_must_match(sqlite_session_factory: SessionFactory) -> None:
    await _index(
        sqlite_session_factory,
        [
            _doc("01J00000000000000000000001", name="ASUS TUF B850 WiFi"),
            _doc(
                "01J00000000000000000000002",
                name="MSI B850 Tomahawk",
                brand="MSI",
                articul=None,
                external_code=None,
            ),
        ],
    )
    async with sqlite_session_factory() as session:
        hits, _ = await search(session, "asus b850")
    assert [h.supplier_product_id for h in hits] == ["01J00000000000000000000001"]


async def test_search__matches_brand_and_articul(sqlite_session_factory: SessionFactory) -> None:
    await _index(sqlite_session_factory, [_doc("01J00000000000000000000001", articul="TUF-XYZ")])
    async with sqlite_session_factory() as session:
        by_brand, _ = await search(session, "asus")
        by_articul, _ = await search(session, "tuf xyz")
    assert len(by_brand) == 1
    assert len(by_articul) == 1


async def test_search__empty_query_returns_nothing(sqlite_session_factory: SessionFactory) -> None:
    await _index(sqlite_session_factory, [_doc("01J00000000000000000000001")])
    async with sqlite_session_factory() as session:
        hits, cursor = await search(session, "   ")
    assert hits == [] and cursor is None


async def test_search__is_cursor_paginated(sqlite_session_factory: SessionFactory) -> None:
    ids = [f"01J0000000000000000000000{i}" for i in range(1, 4)]
    await _index(sqlite_session_factory, [_doc(i, name="ASUS common") for i in ids])
    async with sqlite_session_factory() as session:
        page1, cursor = await search(session, "asus", limit=2)
        assert [h.supplier_product_id for h in page1] == ids[:2]
        assert cursor is not None
        page2, cursor2 = await search(session, "asus", cursor=cursor, limit=2)
    assert [h.supplier_product_id for h in page2] == ids[2:]
    assert cursor2 is None


async def test_index__is_idempotent_upsert(sqlite_session_factory: SessionFactory) -> None:
    await _index(sqlite_session_factory, [_doc("01J00000000000000000000001", name="Old Name")])
    await _index(sqlite_session_factory, [_doc("01J00000000000000000000001", name="New Name")])
    async with sqlite_session_factory() as session:
        row = await session.get(SearchDocumentRow, "01J00000000000000000000001")
    assert row is not None and row.name == "New Name"


async def test_find_by_code_and_articul(sqlite_session_factory: SessionFactory) -> None:
    await _index(
        sqlite_session_factory,
        [_doc("01J00000000000000000000001", external_code="U999", articul="ART-1")],
    )
    async with sqlite_session_factory() as session:
        by_code = await find_by_code(session, "U999")
        by_articul = await find_by_articul(session, "ART-1")
    assert len(by_code) == 1 and len(by_articul) == 1


async def test_find_by_gtin__normalizes(sqlite_session_factory: SessionFactory) -> None:
    # The event carries a GTIN-14; querying with the raw 12-digit UPC still matches after
    # normalization (both map to the same GTIN-14).
    await _index(
        sqlite_session_factory, [_doc("01J00000000000000000000001", gtin="00036000291452")]
    )
    async with sqlite_session_factory() as session:
        hits = await find_by_gtin(session, "036000291452")
        invalid = await find_by_gtin(session, "not-a-gtin")
    assert len(hits) == 1
    assert invalid == []
