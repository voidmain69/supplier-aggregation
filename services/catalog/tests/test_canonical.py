from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from catalog.adapters.repository import canonical_ids_for
from catalog.api.deps import get_session_factory
from catalog.events.handlers import build_discovered_handler, build_link_confirmed_handler
from catalog.main import create_app
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
