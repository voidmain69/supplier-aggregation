"""Normalize Brain API JSON into canonical connector DTOs.

Pure functions (no I/O). This is where all Brain-specific shape knowledge lives — the rest
of the platform only ever sees the canonical DTOs (hard rule 8). Field semantics follow
brain_api_documentation.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sa_connector_sdk.dto import RawCategory, RawOffer, RawProduct, RawStock
from sa_connector_sdk.normalize import extract_gtin, normalize_text
from sa_core.money import Money
from sa_core.time import utc_now

_BRAND_OPTION_NAMES = {"виробник", "производитель", "brand"}
_BRAIN_DATETIME_FMT = "%Y-%m-%d %H:%M:%S"


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", 0, "0", "0.00"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), _BRAIN_DATETIME_FMT).replace(tzinfo=UTC)
    except ValueError:
        return None


def _attributes(options: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold Brain ``options`` into a name->value(s) map, listing repeated names."""
    attributes: dict[str, Any] = {}
    for option in options:
        name = normalize_text(option.get("name"))
        value = normalize_text(str(option.get("value", "")))
        if not name or value is None:
            continue
        if name in attributes:
            existing = attributes[name]
            attributes[name] = (
                [*existing, value] if isinstance(existing, list) else [existing, value]
            )
        else:
            attributes[name] = value
    return attributes


def _brand(options: list[dict[str, Any]]) -> str | None:
    for option in options:
        if normalize_text(option.get("name") or "").lower() in _BRAND_OPTION_NAMES:  # type: ignore[union-attr]
            return normalize_text(str(option.get("value", "")))
    return None


def _images(raw: dict[str, Any]) -> list[str]:
    for key in ("full_image", "large_image", "medium_image", "small_image"):
        url = raw.get(key)
        if url:
            return [str(url)]
    return []


def normalize_product(raw: dict[str, Any]) -> RawProduct:
    ean = raw.get("EAN")
    options = raw.get("options") or []
    return RawProduct(
        external_id=str(raw["productID"]),
        external_code=raw.get("product_code"),
        articul=normalize_text(raw.get("articul")),
        name=normalize_text(raw.get("name")) or str(raw["productID"]),
        brand=_brand(options),
        gtin=extract_gtin(ean),
        raw_identifiers={"ean": str(ean)} if ean else {},
        attributes=_attributes(options),
        supplier_category_id=str(raw["categoryID"]) if raw.get("categoryID") else None,
        images=_images(raw),
    )


def normalize_offer(raw: dict[str, Any], *, settlement_currency: str) -> RawOffer:
    price_value = _to_decimal(raw.get("price"))
    price_uah = _to_decimal(raw.get("price_uah"))
    if price_value is not None:
        price = Money.of(price_value, settlement_currency)
    elif price_uah is not None:
        price = Money.of(price_uah, "UAH")
    else:
        raise ValueError(f"Brain product {raw.get('productID')} has no usable price")

    retail = _to_decimal(raw.get("retail_price_uah"))
    available = raw.get("available") or {}
    expected = raw.get("stocks_expected") or {}
    return RawOffer(
        external_id=str(raw["productID"]),
        external_code=raw.get("product_code"),
        price=price,
        price_uah=price_uah,
        rrp=Money.of(retail, "UAH") if retail is not None else None,
        stocks={str(k): int(v) for k, v in available.items()},
        expected={str(k): dt for k, v in expected.items() if (dt := _parse_dt(v)) is not None},
        observed_at=utc_now(),
    )


def normalize_category(raw: dict[str, Any]) -> RawCategory:
    parent = raw.get("parentID") or raw.get("parent_id")
    return RawCategory(
        external_id=str(raw["categoryID"]),
        name=normalize_text(raw.get("name")) or str(raw["categoryID"]),
        parent_id=str(parent) if parent not in (None, 0, "0") else None,
    )


def normalize_stock(raw: dict[str, Any]) -> RawStock:
    return RawStock(
        external_id=str(raw["stockID"]),
        name=normalize_text(raw.get("name")) or str(raw["stockID"]),
        city=normalize_text(raw.get("city")),
    )
