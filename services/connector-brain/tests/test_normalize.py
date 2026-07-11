from __future__ import annotations

from decimal import Decimal
from typing import Any

from connector_brain.domain import normalize

from sa_core.money import Money


def test_normalize_product__maps_canonical_fields(brain_fixtures: dict[str, Any]) -> None:
    product = normalize.normalize_product(brain_fixtures["product"])

    assert product.external_id == "100463720"
    assert product.external_code == "U1005797"
    assert product.articul == "TUF GAMING B850-PLUS WIFI"
    assert product.gtin == "04711387781609"  # EAN normalized to GTIN-14
    assert product.raw_identifiers == {"ean": "4711387781609"}
    assert product.brand == "ASUS"
    assert product.supplier_category_id == "1264"
    assert product.images == [
        "https://opt.brain.com.ua/static/images/prod_img/9/7/U1005797_main.jpg"
    ]


def test_normalize_product__repeated_option_names_become_list(
    brain_fixtures: dict[str, Any],
) -> None:
    product = normalize.normalize_product(brain_fixtures["product"])
    assert product.attributes["Сокет"] == "AM5"
    assert product.attributes["Слоти розширення"] == [
        "1 x PCI-E 4.0 x16",
        "2 x PCI-E 4.0 x1",
    ]


def test_normalize_offer__price_stock_and_rrp(brain_fixtures: dict[str, Any]) -> None:
    offer = normalize.normalize_offer(brain_fixtures["product"], settlement_currency="USD")

    assert offer.price == Money.of("222.22", "USD")
    assert offer.price_uah == Decimal("9900.00")
    assert offer.rrp == Money.of("9999.00", "UAH")
    assert offer.stocks == {"1": 3, "121": 2}
    assert "19" in offer.expected
    assert offer.observed_at.tzinfo is not None


def test_normalize_offer__falls_back_to_uah_when_no_base_price() -> None:
    offer = normalize.normalize_offer(
        {"productID": 1, "price_uah": "500.00"}, settlement_currency="USD"
    )
    assert offer.price == Money.of("500.00", "UAH")


def test_normalize_category_and_stock(brain_fixtures: dict[str, Any]) -> None:
    category = normalize.normalize_category(brain_fixtures["categories"][0])
    assert category.external_id == "1264"
    assert category.parent_id == "125"

    root = normalize.normalize_category(brain_fixtures["categories"][1])
    assert root.parent_id is None  # parentID 0 -> no parent

    stock = normalize.normalize_stock(brain_fixtures["stocks"][0])
    assert stock.external_id == "1"
    assert stock.city == "Київ"
