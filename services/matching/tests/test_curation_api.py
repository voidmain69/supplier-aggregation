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


async def test_confirm__records_operator_from_gateway_header(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        resp = await client.post(
            f"/v1/curation/links/{_SPID}/confirm", headers={"X-Operator-Id": "user:alice"}
        )
        assert resp.status_code == 200
    async with sqlite_session_factory() as session:
        link = await get_link(session, _SPID)
    assert link is not None
    assert link.decided_by == "user:alice"  # audit reflects the real operator, not a placeholder


async def test_confirm__without_header_falls_back_to_generic_operator(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        await client.post(f"/v1/curation/links/{_SPID}/confirm")
    async with sqlite_session_factory() as session:
        link = await get_link(session, _SPID)
    assert link is not None
    assert link.decided_by == "operator"


async def test_create_new__links_a_fresh_confirmed_canonical(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with sqlite_session_factory() as session:
        draft_canonical_id = (await get_link(session, _SPID)).canonical_product_id  # type: ignore[union-attr]

    async with client:
        resp = await client.post(
            f"/v1/curation/links/{_SPID}/create-new",
            json={"title": "Acme Widget Pro", "brand": "Acme", "gtin": None},
            headers={"X-Operator-Id": "user:alice"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "confirmed"
    assert body["canonical_product_id"] != draft_canonical_id  # a brand-new canonical

    async with sqlite_session_factory() as session:
        link = await get_link(session, _SPID)
        assert link is not None
        assert link.method == "manual"
        assert link.decided_by == "user:alice"
        canonical = await session.get(CanonicalProductRow, link.canonical_product_id)
    assert canonical is not None
    assert canonical.title == "Acme Widget Pro"
    assert canonical.status == "confirmed"

    publisher = InMemoryPublisher()
    assert await OutboxRelay(sqlite_session_factory, publisher).drain() == 1  # confirmation emitted


async def test_create_new__rejects_a_gtin_already_on_another_canonical(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    # A GTIN product auto-creates a canonical carrying that GTIN.
    other = "01J0000000000000000PROD2"
    await build_discovered_handler(sqlite_session_factory)(
        discovered_event(supplier_product_id=other, gtin="04711387781609", name="Has a GTIN")
    )
    await _stage_pending(sqlite_session_factory, discovered_event)

    async with client:
        resp = await client.post(
            f"/v1/curation/links/{_SPID}/create-new",
            json={"title": "Dup", "gtin": "04711387781609"},
        )
    assert resp.status_code == 409
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_create_new__409_when_already_confirmed(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        await client.post(f"/v1/curation/links/{_SPID}/confirm")
        resp = await client.post(
            f"/v1/curation/links/{_SPID}/create-new", json={"title": "Too late"}
        )
    assert resp.status_code == 409
