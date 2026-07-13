"""Canonical card aggregation — pure domain, no I/O."""

from __future__ import annotations

from typing import Any

from catalog.domain.canonical import MemberProduct, build_canonical_card


def _member(
    spid: str,
    name: str,
    *,
    brand: str | None = None,
    gtin: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> MemberProduct:
    return MemberProduct(spid, name, brand, gtin, attributes or {})


def test_build__representative_title_is_lowest_supplier_product_id() -> None:
    card = build_canonical_card(
        [
            _member("01J00000000000000000000002", "second"),
            _member("01J00000000000000000000001", "first"),
        ]
    )
    assert card.title == "first"


def test_build__brand_and_gtin_take_first_member_that_has_one() -> None:
    card = build_canonical_card(
        [
            _member("01J00000000000000000000001", "n1", brand=None, gtin=None),
            _member("01J00000000000000000000002", "n2", brand="Acme", gtin="04711387781609"),
        ]
    )
    assert card.brand == "Acme"
    assert card.gtin == "04711387781609"


def test_build__attributes_merged_lowest_id_wins_on_conflict() -> None:
    card = build_canonical_card(
        [
            _member("01J00000000000000000000001", "n1", attributes={"k": "low", "only1": 1}),
            _member("01J00000000000000000000002", "n2", attributes={"k": "high", "only2": 2}),
        ]
    )
    assert card.attributes == {"k": "low", "only1": 1, "only2": 2}
