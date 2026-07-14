"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from catalog.adapters.models import CanonicalProductRow, SupplierProductRow


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class CanonicalProductOut(BaseModel):
    """The canonical (platform) product card the catalog owns (ADR-0012)."""

    canonical_product_id: str = Field(description="Stable internal ULID of the canonical product.")
    title: str = Field(description="Canonical product title (deterministic merge of members).")
    brand: str | None = Field(default=None, description="Brand/vendor name, if known.")
    gtin: str | None = Field(
        default=None,
        description="Normalized GTIN-14 shared by the members, or null if none carries one.",
    )
    status: str = Field(description="Card status; currently always 'confirmed'.")
    attributes: dict[str, object] = Field(
        default_factory=dict,
        description="Merged attribute map from all member supplier products.",
    )
    supplier_product_ids: list[str] = Field(
        default_factory=list,
        description="Member supplier products (ULIDs, sorted). Fetch each via "
        "GET /v1/supplier-products/{id} to compare supplier versions.",
    )
    updated_at: datetime = Field(description="When the card was last rebuilt (UTC).")

    @classmethod
    def from_row(cls, row: CanonicalProductRow) -> CanonicalProductOut:
        return cls(
            canonical_product_id=row.canonical_product_id,
            title=row.title,
            brand=row.brand,
            gtin=row.gtin,
            status=row.status,
            attributes=row.attributes,
            supplier_product_ids=row.supplier_product_ids,
            updated_at=row.updated_at,
        )


class SupplierProductOut(BaseModel):
    """A single supplier product as held by the catalog."""

    supplier_product_id: str = Field(
        description="Stable internal ULID of this supplier product. Use it in "
        "GET /v1/supplier-products/{id} and as the cursor anchor."
    )
    supplier_code: str = Field(description="Short code of the supplier, e.g. 'brain'.")
    external_id: str = Field(description="The supplier's own product id (opaque to us).")
    external_code: str | None = Field(
        default=None, description="The supplier's human product code, if any."
    )
    articul: str | None = Field(default=None, description="Manufacturer part number (MPN).")
    gtin: str | None = Field(
        default=None,
        description="Normalized GTIN-14 (from EAN/UPC), or null if absent/invalid. "
        "Use it to match the same product across suppliers.",
    )
    name: str = Field(description="Product name as provided by the supplier.")
    brand: str | None = Field(default=None, description="Brand/vendor name, if known.")
    supplier_category_id: str | None = Field(
        default=None, description="The supplier's category id for this product."
    )
    attributes: dict[str, object] = Field(
        default_factory=dict,
        description="Normalized attribute map (name -> value or list of values).",
    )
    canonical_product_id: str | None = Field(
        default=None,
        description="Internal id of the canonical product this maps to (once matched), or "
        "null if not matched yet. Use it to find the same product across suppliers.",
    )

    @classmethod
    def from_row(
        cls, row: SupplierProductRow, *, canonical_product_id: str | None = None
    ) -> SupplierProductOut:
        return cls(
            supplier_product_id=row.supplier_product_id,
            supplier_code=row.supplier_code,
            external_id=row.external_id,
            external_code=row.external_code,
            articul=row.articul,
            gtin=row.gtin,
            name=row.name,
            brand=row.brand,
            supplier_category_id=row.supplier_category_id,
            attributes=row.attributes,
            canonical_product_id=canonical_product_id,
        )
