"""Decision journal: every curation decision is recorded and listed (SQLite)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from matching.api.deps import get_session_factory
from matching.events.handlers import build_discovered_handler
from matching.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]
_SPID = "01J0000000000000000PROD1"


async def _stage_pending(
    factory: SessionFactory, discovered_event: Callable[..., dict[str, Any]]
) -> None:
    await build_discovered_handler(factory)(
        discovered_event(supplier_product_id=_SPID, gtin=None, name="Unique widget xyz")
    )


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_confirm__records_a_confirm_decision(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        await client.post(
            f"/v1/curation/links/{_SPID}/confirm", headers={"X-Operator-Id": "op:alice"}
        )
        body = (await client.get("/v1/curation/decisions")).json()

    assert len(body["items"]) == 1
    decision = body["items"][0]
    assert decision["action"] == "confirm"
    assert decision["supplier_product_id"] == _SPID
    assert decision["operator"] == "op:alice"
    assert decision["decided_at"]


async def test_create_new__records_create_new_decision(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        await client.post(
            f"/v1/curation/links/{_SPID}/create-new", json={"title": "Brand New Widget"}
        )
        body = (await client.get("/v1/curation/decisions")).json()

    decision = body["items"][0]
    assert decision["action"] == "create_new"
    assert decision["note"] == "new canonical: Brand New Widget"


async def test_decisions__filter_by_supplier_product(
    client: httpx.AsyncClient,
    sqlite_session_factory: SessionFactory,
    discovered_event: Callable[..., dict[str, Any]],
) -> None:
    await _stage_pending(sqlite_session_factory, discovered_event)
    async with client:
        await client.post(f"/v1/curation/links/{_SPID}/reject")
        matched = (
            await client.get("/v1/curation/decisions", params={"supplier_product_id": _SPID})
        ).json()
        other = (
            await client.get(
                "/v1/curation/decisions", params={"supplier_product_id": "01J0000000000000000OTHER"}
            )
        ).json()

    assert [d["action"] for d in matched["items"]] == ["reject"]
    assert other["items"] == []
