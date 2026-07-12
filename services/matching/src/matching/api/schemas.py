"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from matching.adapters.models import CanonicalProductRow


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class CanonicalProductOut(BaseModel):
    """A canonical (platform) product that aggregates supplier products."""

    canonical_product_id: str = Field(description="Stable internal ULID of the canonical product.")
    gtin: str | None = Field(
        default=None, description="Normalized GTIN-14, if the product was matched by GTIN."
    )
    brand: str | None = Field(default=None, description="Brand/vendor name, if known.")
    title: str = Field(description="Canonical product title.")

    @classmethod
    def from_row(cls, row: CanonicalProductRow) -> CanonicalProductOut:
        return cls(
            canonical_product_id=row.canonical_product_id,
            gtin=row.gtin,
            brand=row.brand,
            title=row.title,
        )
