from __future__ import annotations

import httpx
import pytest
from catalog.adapters.repository import upsert_supplier_product
from catalog.api.deps import get_session_factory
from catalog.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_product_discovered import SupplierProductDiscovered

SessionFactory = async_sessionmaker[AsyncSession]


async def _seed(factory: SessionFactory, ids: list[str]) -> None:
    async with factory() as session, session.begin():
        for i, spid in enumerate(ids):
            await upsert_supplier_product(
                session,
                SupplierProductDiscovered(
                    schema_version=1,
                    supplier_product_id=spid,
                    supplier_code="brain",
                    external_id=f"e{i}",
                    name=f"Product {i}",
                    gtin="04711387781609",
                    sync_job_id="01JSYNC",
                ),
            )


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_list__paginates(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    ids = ["01J0000000000000000000P1", "01J0000000000000000000P2", "01J0000000000000000000P3"]
    await _seed(sqlite_session_factory, ids)

    async with client:
        first = (await client.get("/v1/supplier-products", params={"limit": 2})).json()
        assert [p["supplier_product_id"] for p in first["items"]] == ids[:2]
        assert first["next_cursor"] is not None

        second = (
            await client.get(
                "/v1/supplier-products", params={"limit": 2, "cursor": first["next_cursor"]}
            )
        ).json()
        assert [p["supplier_product_id"] for p in second["items"]] == ids[2:]
        assert second["next_cursor"] is None


async def test_get__found(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(sqlite_session_factory, ["01J0000000000000000000P1"])
    async with client:
        resp = await client.get("/v1/supplier-products/01J0000000000000000000P1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gtin"] == "04711387781609"
    assert body["supplier_code"] == "brain"


async def test_get__missing_returns_problem_json(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.get("/v1/supplier-products/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("/not-found")
