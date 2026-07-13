from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from matching.adapters.models import CanonicalProductRow
from matching.adapters.repository import get_link
from matching.api.deps import get_session_factory
from matching.events.handlers import build_discovered_handler
from matching.main import create_app
from sa_persistence.relay import InMemoryPublisher, OutboxRelay
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]
_P1 = "01J0000000000000000PROD1"
_P2 = "01J0000000000000000PROD2"


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _canonical_of(factory: SessionFactory, supplier_product_id: str) -> str:
    async with factory() as session:
        link = await get_link(session, supplier_product_id)
    assert link is not None
    return link.canonical_product_id


async def _stage_two_canonicals(
    factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> tuple[str, str]:
    handle = build_discovered_handler(factory)
    await handle(discovered_event(supplier_product_id=_P1, gtin="04711387781609", name="Board A"))
    await handle(discovered_event(supplier_product_id=_P2, gtin="05010029000010", name="Board B"))
    return await _canonical_of(factory, _P1), await _canonical_of(factory, _P2)


async def test_merge__moves_links_and_removes_source(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    target, source = await _stage_two_canonicals(sqlite_session_factory, discovered_event)

    async with client:
        resp = await client.post(
            f"/v1/canonical-products/{target}/merge",
            json={"source_canonical_product_id": source},
            headers={"X-Operator-Id": "user:bob"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["moved_links"] == 1
    assert body["target_canonical_product_id"] == target

    async with sqlite_session_factory() as session:
        moved = await get_link(session, _P2)
        assert moved is not None
        assert moved.canonical_product_id == target  # repointed to the target
        assert moved.decided_by == "user:bob"
        assert await session.get(CanonicalProductRow, source) is None  # source removed

    publisher = InMemoryPublisher()
    # Discovery enqueued one confirmation per GTIN product (P1->target, P2->source); the merge
    # re-emits P2 against the target. So three events drain, two of them pointing at the target.
    drained = await OutboxRelay(sqlite_session_factory, publisher).drain()
    assert drained == 3
    to_target = [
        p for _t, _k, p in publisher.published if p["data"]["canonical_product_id"] == target
    ]
    assert len(to_target) == 2


async def test_merge__into_itself_is_409(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    target, _ = await _stage_two_canonicals(sqlite_session_factory, discovered_event)
    async with client:
        resp = await client.post(
            f"/v1/canonical-products/{target}/merge",
            json={"source_canonical_product_id": target},
        )
    assert resp.status_code == 409


async def test_merge__unknown_source_is_404(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    target, _ = await _stage_two_canonicals(sqlite_session_factory, discovered_event)
    async with client:
        resp = await client.post(
            f"/v1/canonical-products/{target}/merge",
            json={"source_canonical_product_id": "01J000000000000000MISSING"},
        )
    assert resp.status_code == 404
