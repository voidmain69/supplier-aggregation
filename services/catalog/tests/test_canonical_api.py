from __future__ import annotations

import httpx
import pytest
from catalog.adapters.repository import (
    rebuild_canonical_card,
    set_canonical_link,
    upsert_supplier_product,
)
from catalog.api.deps import get_session_factory
from catalog.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

SessionFactory = async_sessionmaker[AsyncSession]


async def _seed_canonical(
    factory: SessionFactory,
    canonical_product_id: str,
    member_ids: list[str],
    *,
    gtin: str | None = "04711387781609",
) -> None:
    """Ingest member supplier products, link them, and rebuild the canonical card."""
    async with factory() as session, session.begin():
        for i, spid in enumerate(member_ids):
            await upsert_supplier_product(
                session,
                SupplierProductDiscovered(
                    schema_version=1,
                    supplier_product_id=spid,
                    supplier_code="brain",
                    external_id=f"e-{canonical_product_id}-{i}",
                    name=f"Product {spid}",
                    brand="ASUS",
                    gtin=gtin,
                    attributes={"Socket": "AM5"},
                    sync_job_id="01JSYNC",
                ),
            )
            await set_canonical_link(
                session, supplier_product_id=spid, canonical_product_id=canonical_product_id
            )
        await rebuild_canonical_card(session, canonical_product_id)


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_list_canonical__paginates(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    ids = ["01J0000000000000000000C1", "01J0000000000000000000C2", "01J0000000000000000000C3"]
    for i, cid in enumerate(ids):
        await _seed_canonical(sqlite_session_factory, cid, [f"01J0000000000000000000P{i}"])

    async with client:
        first = (await client.get("/v1/canonical-products", params={"limit": 2})).json()
        assert [p["canonical_product_id"] for p in first["items"]] == ids[:2]
        assert first["next_cursor"] is not None

        second = (
            await client.get(
                "/v1/canonical-products", params={"limit": 2, "cursor": first["next_cursor"]}
            )
        ).json()
        assert [p["canonical_product_id"] for p in second["items"]] == ids[2:]
        assert second["next_cursor"] is None


async def test_list_canonical__filters_by_gtin(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed_canonical(
        sqlite_session_factory,
        "01J0000000000000000000C1",
        ["01J0000000000000000000P1"],
        gtin="04711387781609",
    )
    await _seed_canonical(
        sqlite_session_factory,
        "01J0000000000000000000C2",
        ["01J0000000000000000000P2"],
        gtin=None,
    )

    async with client:
        body = (
            await client.get("/v1/canonical-products", params={"gtin": "04711387781609"})
        ).json()
    assert [p["canonical_product_id"] for p in body["items"]] == ["01J0000000000000000000C1"]


async def test_get_canonical__returns_card_with_members(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    members = ["01J0000000000000000000P1", "01J0000000000000000000P2"]
    await _seed_canonical(sqlite_session_factory, "01J0000000000000000000C1", members)

    async with client:
        resp = await client.get("/v1/canonical-products/01J0000000000000000000C1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Product 01J0000000000000000000P1"
    assert body["brand"] == "ASUS"
    assert body["gtin"] == "04711387781609"
    assert body["status"] == "confirmed"
    assert body["attributes"] == {"Socket": "AM5"}
    assert body["supplier_product_ids"] == members
    assert body["updated_at"] is not None


async def test_get_canonical__missing_returns_problem_json(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.get("/v1/canonical-products/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("/not-found")
