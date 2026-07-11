"""Canonical connector DTOs — the normalized boundary between a supplier and the platform.

A connector's job is to turn supplier-specific responses into these types. Everything
downstream (catalog, offer, matching) speaks these, never a supplier's raw shape — so a
new supplier means a new connector, not changes in core services (hard rule 8).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from sa_core.money import Money

DeltaKind = Literal["images", "descriptions", "options", "new", "all"]


class ConnectorHealth(BaseModel):
    """Result of a connector healthcheck (auth reachable, within rate budget)."""

    model_config = ConfigDict(frozen=True)

    ok: bool
    detail: str | None = None
    latency_ms: float | None = None


class AccountCtx(BaseModel):
    """A supplier account the connector acts on behalf of.

    Carries no secrets — only ``credentials_ref`` (a Vault path); the connector resolves
    the actual credentials at auth time (hard rule 6).
    """

    model_config = ConfigDict(frozen=True)

    account_id: str
    supplier_code: str
    credentials_ref: str
    settlement_currency: str
    settings: dict[str, Any] = Field(default_factory=dict)


class ProductRef(BaseModel):
    """References a single product for ``fetch_product`` by exactly one identifier."""

    model_config = ConfigDict(frozen=True)

    external_id: str | None = None
    articul: str | None = None
    product_code: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> ProductRef:
        provided = [v for v in (self.external_id, self.articul, self.product_code) if v]
        if len(provided) != 1:
            raise ValueError("ProductRef needs exactly one of external_id/articul/product_code")
        return self

    @classmethod
    def by_id(cls, external_id: str) -> ProductRef:
        return cls(external_id=external_id)

    @classmethod
    def by_articul(cls, articul: str) -> ProductRef:
        return cls(articul=articul)

    @classmethod
    def by_code(cls, product_code: str) -> ProductRef:
        return cls(product_code=product_code)


class RawCategory(BaseModel):
    """A supplier category node (before mapping to the platform's own tree)."""

    model_config = ConfigDict(frozen=True)

    external_id: str
    name: str
    parent_id: str | None = None


class RawStock(BaseModel):
    """A supplier warehouse/stock location (for self-describing availability)."""

    model_config = ConfigDict(frozen=True)

    external_id: str
    name: str
    city: str | None = None


class DeltaRef(BaseModel):
    """A pointer to a changed product returned by a delta sync."""

    model_config = ConfigDict(frozen=True)

    external_id: str
    kind: DeltaKind = "all"


class RawProduct(BaseModel):
    """A supplier product normalized to canonical fields (catalog content, not pricing)."""

    model_config = ConfigDict(frozen=True)

    external_id: str
    external_code: str | None = None
    articul: str | None = None
    name: str
    brand: str | None = None
    gtin: str | None = None
    """Normalized GTIN-14, or None when absent/invalid (raw kept in ``raw_identifiers``)."""
    raw_identifiers: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, Any] = Field(default_factory=dict)
    supplier_category_id: str | None = None
    images: list[str] = Field(default_factory=list)

    def content_fields(self) -> dict[str, Any]:
        """The subset used for change detection (excludes nothing volatile here)."""
        return {
            "external_code": self.external_code,
            "articul": self.articul,
            "name": self.name,
            "brand": self.brand,
            "gtin": self.gtin,
            "raw_identifiers": self.raw_identifiers,
            "attributes": self.attributes,
            "supplier_category_id": self.supplier_category_id,
            "images": self.images,
        }


class RawOffer(BaseModel):
    """A supplier's price and availability for one product, under one account."""

    model_config = ConfigDict(frozen=True)

    external_id: str
    external_code: str | None = None
    price: Money
    price_uah: Decimal | None = None
    rrp: Money | None = None
    stocks: dict[str, int] = Field(default_factory=dict)
    """Available quantity per stock location id."""
    expected: dict[str, AwareDatetime] = Field(default_factory=dict)
    """Restock ETA per stock location id, when the supplier provides it."""
    observed_at: AwareDatetime
