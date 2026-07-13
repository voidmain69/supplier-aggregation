from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from offer.adapters.repository import upsert_offer
from offer.api.deps import get_session_factory
from offer.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sa_contracts.events.supplier_offer_price_changed import SupplierOfferPriceChanged

SessionFactory = async_sessionmaker[AsyncSession]
_PROD = "01J0000000000000000PROD1"


async def _seed(factory: SessionFactory, offers: list[tuple[str, str]]) -> None:
    async with factory() as session, session.begin():
        for offer_id, price_uah in offers:
            await upsert_offer(
                session,
                SupplierOfferPriceChanged(
                    schema_version=1,
                    offer_id=offer_id,
                    supplier_account_id="01J0000000000000000ACCT1",
                    supplier_product_id=_PROD,
                    new_price="222.2200",
                    currency="USD",
                    price_uah=price_uah,
                    observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
                    sync_job_id="01JSYNC",
                ),
            )


@pytest.fixture
def client(sqlite_session_factory: SessionFactory) -> httpx.AsyncClient:
    app = create_app()
    app.dependency_overrides[get_session_factory] = lambda: sqlite_session_factory
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_list_offers__by_product(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(
        sqlite_session_factory,
        [("01J000000000000000OFFER01", "9900.0000"), ("01J000000000000000OFFER02", "9500.0000")],
    )
    async with client:
        body = (await client.get("/v1/offers", params={"supplier_product_id": _PROD})).json()
    assert {o["offer_id"] for o in body["items"]} == {
        "01J000000000000000OFFER01",
        "01J000000000000000OFFER02",
    }


async def test_best_offer__returns_cheapest(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(
        sqlite_session_factory,
        [("01J000000000000000OFFER01", "9900.0000"), ("01J000000000000000OFFER02", "9500.0000")],
    )
    async with client:
        resp = await client.get("/v1/offers/best", params={"supplier_product_id": _PROD})
    assert resp.status_code == 200
    assert resp.json()["offer_id"] == "01J000000000000000OFFER02"


async def test_best_offer__404_problem_json_when_none(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.get("/v1/offers/best", params={"supplier_product_id": "nope"})
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("/not-found")


async def test_get_offer__found_and_missing(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(sqlite_session_factory, [("01J000000000000000OFFER01", "9900.0000")])
    async with client:
        ok = await client.get("/v1/offers/01J000000000000000OFFER01")
        missing = await client.get("/v1/offers/does-not-exist")
    assert ok.status_code == 200
    assert ok.json()["price_uah"] == "9900.0000"
    # No terms set: USD with no FX falls back to supplier price_uah, so effective == price_uah.
    assert ok.json()["effective_price_uah"] == "9900.0000"
    assert missing.status_code == 404


async def test_put_account_terms__reprices_and_changes_effective(
    client: httpx.AsyncClient, sqlite_session_factory: SessionFactory
) -> None:
    await _seed(sqlite_session_factory, [("01J000000000000000OFFER01", "1000.0000")])
    async with client:
        resp = await client.put(
            "/v1/accounts/01J0000000000000000ACCT1/terms",
            json={"discount_pct": "0.25"},
        )
        assert resp.status_code == 200
        assert resp.json()["offers_repriced"] == 1

        offer = (await client.get("/v1/offers/01J000000000000000OFFER01")).json()
    assert offer["effective_price_uah"] == "750.0000"  # 1000 * 0.75


async def test_put_account_terms__rejects_invalid_discount(client: httpx.AsyncClient) -> None:
    async with client:
        resp = await client.put(
            "/v1/accounts/01J0000000000000000ACCT1/terms", json={"discount_pct": "1.5"}
        )
    assert resp.status_code == 422
