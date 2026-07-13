"""Canonical product card aggregation (pure domain — no I/O).

The catalog owns the canonical (platform) product. Matching decides *which* supplier products form
a canonical (and emits ``matching.link.confirmed``); the catalog then *rebuilds the card* by
aggregating those member supplier products into a single title/brand/gtin/attributes view. This
module is the pure aggregation rule; the repository feeds it members and persists the result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemberProduct:
    """A supplier product that belongs to a canonical, reduced to the fields the card needs."""

    supplier_product_id: str
    name: str
    brand: str | None
    gtin: str | None
    attributes: dict[str, Any]


@dataclass(frozen=True)
class CanonicalCard:
    """The aggregated canonical view built from member supplier products."""

    title: str
    brand: str | None
    gtin: str | None
    attributes: dict[str, Any]


def build_canonical_card(members: list[MemberProduct]) -> CanonicalCard:
    """Aggregate member supplier products into a canonical card.

    Deterministic so the same membership always yields the same card (idempotent re-emit): members
    are ordered by ``supplier_product_id`` and the lowest id is the representative for the title.
    Brand and GTIN take the first member that carries one; attributes are merged with earlier
    (lower-id) members winning on key conflicts. ``members`` must be non-empty.
    """
    ordered = sorted(members, key=lambda member: member.supplier_product_id)
    attributes: dict[str, Any] = {}
    for member in reversed(ordered):
        attributes.update(member.attributes)  # reversed so the lowest-id member wins conflicts
    return CanonicalCard(
        title=ordered[0].name,
        brand=next((member.brand for member in ordered if member.brand), None),
        gtin=next((member.gtin for member in ordered if member.gtin), None),
        attributes=attributes,
    )
