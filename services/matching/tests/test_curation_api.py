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
_SPID = "01J0000000000000000PROD1"


async def _stage_pending(
    factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    # a no-GTIN product with no existing canonical -> a pending_review link to a draft
    await build_discovered_handler(factory)(
        discovered_event(supplier_product_id=_SPID, gtin=None, name="Unique widget xyz")
    )


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_queue__lists_pending(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        body = (await client.get("/v1/curation/queue")).json()
    assert [i["supplier_product_id"] for i in body["items"]] == [_SPID]
    assert body["items"][0]["status"] == "pending_review"


async def test_confirm__updates_status_emits_and_confirms_draft(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        resp = await client.post(f"/v1/curation/links/{_SPID}/confirm")
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
        # idempotent: confirming again is a no-op
        assert (await client.post(f"/v1/curation/links/{_SPID}/confirm")).json()["status"] == (
            "confirmed"
        )

    async with sqlite_session_factory() as session:
        link = await get_link(session, _SPID)
        assert link is not None
        canonical = await session.get(CanonicalProductRow, link.canonical_product_id)
    assert canonical is not None
    assert canonical.status == "confirmed"  # draft got confirmed

    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1  # exactly one emit
    _t, _k, payload = publisher.published[0]
    assert payload["data"]["method"] == "manual"


async def test_reject__updates_status_and_blocks_confirm(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        rejected = await client.post(f"/v1/curation/links/{_SPID}/reject")
        assert rejected.json()["status"] == "rejected"
        conflict = await client.post(f"/v1/curation/links/{_SPID}/confirm")
    assert conflict.status_code == 409
    assert conflict.headers["content-type"].startswith("application/problem+json")


async def test_decision__404_for_unknown(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.post("/v1/curation/links/nope/confirm")
    assert resp.status_code == 404
