from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sa_connector_sdk.dto import ProductRef, RawOffer, RawProduct
from sa_connector_sdk.normalize import content_hash
from sa_core.money import Money


def test_product_ref__exactly_one_identifier() -> None:
    assert ProductRef.by_id("100463720").external_id == "100463720"
    assert ProductRef.by_articul("TUF-B850").articul == "TUF-B850"
    assert ProductRef.by_code("U1005797").product_code == "U1005797"


def test_product_ref__zero_or_multiple__rejected() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ProductRef()
    with pytest.raises(ValueError, match="exactly one"):
        ProductRef(external_id="1", articul="2")


def test_raw_product__content_fields_drive_a_stable_hash() -> None:
    product = RawProduct(
        external_id="100463720",
        name="ASUS TUF GAMING B850-PLUS WIFI",
        gtin="04711387781609",
        attributes={"socket": "AM5", "chipset": "AMD B850"},
    )
    same = product.model_copy(update={"attributes": {"chipset": "AMD B850", "socket": "AM5"}})
    changed = product.model_copy(update={"name": "renamed"})

    assert content_hash(product.content_fields()) == content_hash(same.content_fields())
    assert content_hash(product.content_fields()) != content_hash(changed.content_fields())


def test_raw_offer__money_and_stocks() -> None:
    offer = RawOffer(
        external_id="100463720",
        price=Money.of("222.22", "USD"),
        price_uah=Decimal("9900.00"),
        stocks={"1": 3, "121": 2},
        observed_at=datetime(2026, 7, 11, 10, 0, tzinfo=UTC),
    )
    assert offer.price.currency == "USD"
    assert offer.stocks["1"] == 3
    assert offer.price_uah == Decimal("9900.00")
