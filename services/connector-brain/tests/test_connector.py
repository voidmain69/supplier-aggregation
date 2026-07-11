from __future__ import annotations

from datetime import UTC, datetime

from sa_connector_sdk.dto import AccountCtx, ProductRef
from sa_connector_sdk.raw_archive import InMemoryRawArchive
from sa_connector_sdk.testkit import collect, implements_connector


def test_brain_connector__satisfies_protocol(build_connector) -> None:
    connector, _ = build_connector()
    assert implements_connector(connector)


async def test_fetch_stocks__authenticates_once_and_reuses_sid(
    build_connector, fake_brain, account: AccountCtx
) -> None:
    connector, _ = build_connector()

    stocks = await connector.fetch_stocks(account)
    await connector.fetch_stocks(account)

    assert [s.city for s in stocks] == ["Київ", "Львів"]
    assert fake_brain.auth_calls == 1  # SID cached across calls
    assert len([c for c in fake_brain.get_calls if "/stocks/" in c]) == 2


async def test_fetch_products__paginates_with_cursor(build_connector) -> None:
    connector, _ = build_connector(page_size=1)

    first = await connector.fetch_products("1264", None)
    assert len(first.items) == 1
    assert first.items[0].external_id == "100463720"
    assert first.next_cursor is not None

    second = await connector.fetch_products("1264", first.next_cursor)
    assert second.items == []
    assert second.next_cursor is None


async def test_fetch_product__by_id(build_connector) -> None:
    connector, _ = build_connector()
    product = await connector.fetch_product(ProductRef.by_id("100463720"))
    assert product.gtin == "04711387781609"


async def test_fetch_deltas__streams_changed_ids(build_connector) -> None:
    connector, _ = build_connector()
    deltas = await collect(connector.fetch_deltas(datetime(2026, 7, 11, tzinfo=UTC)))
    assert [d.external_id for d in deltas] == ["100463720", "100463721"]


async def test_fetch_offers__yields_priced_offers_per_product(
    build_connector, account: AccountCtx
) -> None:
    connector, _ = build_connector(page_size=1)
    offers = await collect(connector.fetch_offers(account))
    # 2 categories x 1 product each
    assert len(offers) == 2
    assert all(o.price.currency == "USD" for o in offers)


async def test_session_expired__reauthenticates_once(
    build_connector, fake_brain, account: AccountCtx
) -> None:
    fake_brain.expire_session_once = True
    connector, _ = build_connector()

    stocks = await connector.fetch_stocks(account)
    assert len(stocks) == 2
    assert fake_brain.auth_calls == 2  # re-auth after session-expired error


async def test_raw_responses_are_archived_but_not_auth(
    build_connector, account: AccountCtx
) -> None:
    archive = InMemoryRawArchive()
    connector, store = build_connector(archive=archive)

    await connector.fetch_stocks(account)

    assert len(store.objects) == 1  # the /stocks GET, not the /auth POST
    assert all(key.startswith("raw/brain/") for key in store.objects)
