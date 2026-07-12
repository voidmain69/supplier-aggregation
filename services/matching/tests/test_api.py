from __future__ import annotations

import httpx
import pytest
from matching.adapters.repository import create_canonical
from matching.api.deps import get_session_factory
from matching.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SessionFactory = async_sessionmaker[AsyncSession]


async def _seed(factory: SessionFactory) -> str:
    async with factory() as session, session.begin():
        row = create_canonical(session, gtin="04711387781609", brand="ASUS", title="ASUS TUF B850")
        await session.flush()
        return row.canonical_product_id


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_list__filter_by_gtin(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(sqlite_session_factory)
    async with client:
        body = (
            await client.get("/v1/canonical-products", params={"gtin": "04711387781609"})
        ).json()
    assert len(body["items"]) == 1
    assert body["items"][0]["gtin"] == "04711387781609"


async def test_get__found_and_missing(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    canonical_id = await _seed(sqlite_session_factory)
    async with client:
        found = await client.get(f"/v1/canonical-products/{canonical_id}")
        missing = await client.get("/v1/canonical-products/does-not-exist")
    assert found.status_code == 200
    assert found.json()["title"] == "ASUS TUF B850"
    assert missing.status_code == 404
    assert missing.headers["content-type"].startswith("application/problem+json")
