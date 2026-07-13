from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from catalog.adapters.models import CanonicalProductRow
from catalog.adapters.repository import canonical_ids_for
from catalog.api.deps import get_session_factory
from catalog.events.handlers import build_discovered_handler, build_link_confirmed_handler
from catalog.main import create_app
from sa_persistence.outbox import OutboxRow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]
_SPID = "01J0000000000000000PROD1"
_CANON = "01J0000000000000000CAN01"


async def test_link_handler__records_canonical_mapping(
    sqlite_session_factory: SessionFactory, link_confirmed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_link_confirmed_handler(sqlite_session_factory)
    await handler(link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=_CANON))

    async with sqlite_session_factory() as session:
        mapping = await canonical_ids_for(session, [_SPID])
    assert mapping == {_SPID: _CANON}


async def test_link_handler__idempotent(
    sqlite_session_factory: SessionFactory, link_confirmed_event: Callable[..., dict[str, Any]]
) -> None:
    handler = build_link_confirmed_handler(sqlite_session_factory)
    event = link_confirmed_event(
        supplier_product_id=_SPID, canonical_product_id=_CANON, event_id="01JEVENT1"
    )
    await handler(event)
    await handler(event)  # redelivery -> no error, still one mapping

    async with sqlite_session_factory() as session:
        assert await canonical_ids_for(session, [_SPID]) == {_SPID: _CANON}


async def test_link_before_product__is_not_lost(
    sqlite_session_factory: SessionFactory,
    link_confirmed_event: Callable[..., dict[str, Any]],
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    # link arrives before the product is ingested (ordering race) -> mapping still recorded
    await build_link_confirmed_handler(sqlite_session_factory)(
        link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=_CANON)
    )
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=_SPID)
    )

    async with sqlite_session_factory() as session:
        assert await canonical_ids_for(session, [_SPID]) == {_SPID: _CANON}


async def test_link_confirmed__builds_card_and_emits_catalog_product_updated(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
    link_confirmed_event: Callable[..., dict[str, Any]],
) -> None:
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=_SPID, name="ASUS TUF B850")
    )
    await build_link_confirmed_handler(sqlite_session_factory)(
        link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=_CANON)
    )

    async with sqlite_session_factory() as session:
        card = await session.get(CanonicalProductRow, _CANON)
        outbox = (await session.execute(select(OutboxRow))).scalars().all()

    assert card is not None
    assert card.title == "ASUS TUF B850"
    assert card.brand == "ASUS"
    assert card.gtin == "04711387781609"
    assert card.supplier_product_ids == [_SPID]

    assert len(outbox) == 1
    event = outbox[0]
    assert event.topic == "sa.catalog.product"
    assert event.payload["type"] == "catalog.product.updated"
    assert event.payload["subject"] == _CANON
    assert event.payload["data"]["title"] == "ASUS TUF B850"
    assert event.payload["data"]["supplier_product_ids"] == [_SPID]


async def test_link_confirmed__relink_rebuilds_previous_canonical(
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
    link_confirmed_event: Callable[..., dict[str, Any]],
) -> None:
    other = "01J0000000000000000PROD2"
    old_canon = "01J000000000000000CAN0LD"
    # Two products both linked to old_canon, then _SPID moves to _CANON.
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=_SPID, name="mouse", external_id="e1")
    )
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=other, name="keyboard", external_id="e2")
    )
    link = build_link_confirmed_handler(sqlite_session_factory)
    await link(link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=old_canon))
    await link(link_confirmed_event(supplier_product_id=other, canonical_product_id=old_canon))
    await link(
        link_confirmed_event(
            supplier_product_id=_SPID,
            canonical_product_id=_CANON,
            previous_canonical_product_id=old_canon,
            event_id="01JEVENTRELINK",
        )
    )

    async with sqlite_session_factory() as session:
        moved = await session.get(CanonicalProductRow, _CANON)
        remained = await session.get(CanonicalProductRow, old_canon)

    assert moved is not None and moved.supplier_product_ids == [_SPID]
    # old canonical rebuilt without the moved member
    assert remained is not None and remained.supplier_product_ids == [other]


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_api__exposes_and_filters_by_canonical(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
    link_confirmed_event: Callable[..., dict[str, Any]],
) -> None:
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=_SPID)
    )
    await build_link_confirmed_handler(sqlite_session_factory)(
        link_confirmed_event(supplier_product_id=_SPID, canonical_product_id=_CANON)
    )

    async with client:
        one = (await client.get(f"/v1/supplier-products/{_SPID}")).json()
        assert one["canonical_product_id"] == _CANON

        filtered = (
            await client.get("/v1/supplier-products", params={"canonical_product_id": _CANON})
        ).json()
        assert [p["supplier_product_id"] for p in filtered["items"]] == [_SPID]
        assert filtered["items"][0]["canonical_product_id"] == _CANON
