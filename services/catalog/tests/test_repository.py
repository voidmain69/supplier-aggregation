from __future__ import annotations

from catalog.adapters.repository import (
    get_supplier_product,
    list_supplier_products,
    upsert_supplier_product,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

SessionFactory = async_sessionmaker[AsyncSession]


def _payload(
    supplier_product_id: str, *, name: str = "Item", external_id: str = "e1"
) -> SupplierProductDiscovered:
    return SupplierProductDiscovered(
        schema_version=1,
        supplier_product_id=supplier_product_id,
        supplier_code="brain",
        external_id=external_id,
        name=name,
        sync_job_id="01JSYNC",
    )


async def test_upsert__insert_then_update(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_supplier_product(session, _payload("01J00000000000000000000A", name="Old"))
    async with sqlite_session_factory() as session, session.begin():
        await upsert_supplier_product(session, _payload("01J00000000000000000000A", name="New"))

    async with sqlite_session_factory() as session:
        row = await get_supplier_product(session, "01J00000000000000000000A")
    assert row is not None
    assert row.name == "New"


async def test_get__missing_returns_none(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session:
        assert await get_supplier_product(session, "nope") is None


async def test_list__cursor_pagination(sqlite_session_factory: SessionFactory) -> None:
    ids = ["01J0000000000000000000P1", "01J0000000000000000000P2", "01J0000000000000000000P3"]
    async with sqlite_session_factory() as session, session.begin():
        for external, spid in enumerate(ids):
            await upsert_supplier_product(session, _payload(spid, external_id=f"e{external}"))

    async with sqlite_session_factory() as session:
        page1, cursor1 = await list_supplier_products(session, limit=2)
        assert [r.supplier_product_id for r in page1] == ids[:2]
        assert cursor1 is not None

        page2, cursor2 = await list_supplier_products(session, cursor=cursor1, limit=2)
        assert [r.supplier_product_id for r in page2] == ids[2:]
        assert cursor2 is None


async def test_list__filter_by_supplier(sqlite_session_factory: SessionFactory) -> None:
    async with sqlite_session_factory() as session, session.begin():
        await upsert_supplier_product(session, _payload("01J0000000000000000000P1"))

    async with sqlite_session_factory() as session:
        rows, _ = await list_supplier_products(session, supplier_code="brain")
        assert len(rows) == 1
        empty, _ = await list_supplier_products(session, supplier_code="other")
        assert empty == []
