from __future__ import annotations

from connector_brain.adapters.identity_repo import resolve_and_stage
from connector_brain.sync import sync_products
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_connector_sdk.dto import RawProduct

SessionFactory = async_sessionmaker[AsyncSession]


def _product(external_id: str, name: str = "Item") -> RawProduct:
    return RawProduct(external_id=external_id, name=name)


async def test_sync_products__new_products_emit_discovered(
    sqlite_session_factory: SessionFactory,
) -> None:
    products = [_product("100463720"), _product("100463721")]

    stats = await sync_products(
        sqlite_session_factory, products, supplier_code="brain", sync_job_id="01JSYNC"
    )

    assert stats.discovered == 2
    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 2
    assert {p[0] for p in publisher.published} == {"sa.supplier.product"}


async def test_sync_products__rerun_is_idempotent(
    sqlite_session_factory: SessionFactory,
) -> None:
    products = [_product("100463720")]
    await sync_products(sqlite_session_factory, products, supplier_code="brain", sync_job_id="j1")

    second = await sync_products(
        sqlite_session_factory, products, supplier_code="brain", sync_job_id="j2"
    )

    assert second.discovered == 0
    assert second.unchanged == 1


async def test_sync_products__content_change_is_detected(
    sqlite_session_factory: SessionFactory,
) -> None:
    await sync_products(
        sqlite_session_factory, [_product("1", name="Old")], supplier_code="brain", sync_job_id="j1"
    )

    stats = await sync_products(
        sqlite_session_factory, [_product("1", name="New")], supplier_code="brain", sync_job_id="j2"
    )

    assert stats.discovered == 0
    assert stats.changed == 1


async def test_resolve_and_stage__stable_id_across_syncs(
    sqlite_session_factory: SessionFactory,
) -> None:
    async with sqlite_session_factory() as session, session.begin():
        first, state1 = await resolve_and_stage(
            session, supplier_code="brain", external_id="42", content_hash="h1"
        )
    async with sqlite_session_factory() as session, session.begin():
        second, state2 = await resolve_and_stage(
            session, supplier_code="brain", external_id="42", content_hash="h1"
        )

    assert state1 == "new"
    assert state2 == "unchanged"
    assert first == second  # supplier_product_id is stable
