"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from catalog.adapters.models import SupplierProductRow


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

    @classmethod
    def from_row(cls, row: SupplierProductRow) -> SupplierProductOut:
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
        )
