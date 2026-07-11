from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime

from sa_connector_sdk.dto import (
    AccountCtx,
    ConnectorHealth,
    DeltaRef,
    ProductRef,
    RawCategory,
    RawOffer,
    RawProduct,
    RawStock,
)
from sa_connector_sdk.testkit import collect, implements_connector
from sa_core.money import Money
from sa_core.pagination import Page
from sa_core.time import utc_now


class FakeConnector:
    supplier_code = "fake"

    async def healthcheck(self) -> ConnectorHealth:
        return ConnectorHealth(ok=True)

    async def fetch_categories(self) -> AsyncIterator[RawCategory]:
        yield RawCategory(external_id="1", name="Root")

    async def fetch_products(self, category_id: str, cursor: str | None) -> Page[RawProduct]:
        return Page(items=[RawProduct(external_id="p1", name="P1")], next_cursor=None)

    async def fetch_product(self, ref: ProductRef) -> RawProduct:
        return RawProduct(external_id=ref.external_id or "x", name="P")

    async def fetch_deltas(self, since: datetime) -> AsyncIterator[DeltaRef]:
        yield DeltaRef(external_id="p1", kind="new")

    async def fetch_offers(self, account: AccountCtx) -> AsyncIterator[RawOffer]:
        yield RawOffer(external_id="p1", price=Money.of("1", "USD"), observed_at=utc_now())

    async def fetch_stocks(self, account: AccountCtx) -> list[RawStock]:
        return [RawStock(external_id="1", name="WH")]


class PartialConnector:
    supplier_code = "partial"

    async def healthcheck(self) -> ConnectorHealth:
        return ConnectorHealth(ok=True)


def test_implements_connector__full_impl_passes() -> None:
    assert implements_connector(FakeConnector())


def test_implements_connector__partial_impl_fails() -> None:
    assert not implements_connector(PartialConnector())


async def test_collect__drains_async_iterator() -> None:
    categories = await collect(FakeConnector().fetch_categories())
    assert [c.external_id for c in categories] == ["1"]


async def test_fetch_products__returns_page() -> None:
    page = await FakeConnector().fetch_products("125", None)
    assert page.items[0].external_id == "p1"
    assert page.next_cursor is None
