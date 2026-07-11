"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from offer.adapters.models import OfferRow


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class OfferOut(BaseModel):
    """One supplier offer: a price for a product under a supplier account."""

    offer_id: str = Field(description="Stable internal ULID of this offer.")
    supplier_account_id: str = Field(
        description="Internal id of the supplier account this price belongs to."
    )
    supplier_product_id: str = Field(
        description="Internal id of the product this offer prices. Filter offers by it."
    )
    price: str = Field(description="Supplier base price, decimal string, in `currency`.")
    currency: str = Field(
        description="ISO-4217 code of `price` (the account's settlement currency)."
    )
    price_uah: str | None = Field(
        default=None,
        description="Price converted to UAH (decimal string), or null. Used to rank offers.",
    )
    rrp_uah: str | None = Field(
        default=None, description="Recommended retail price in UAH, if the supplier provides it."
    )
    observed_at: str = Field(description="When the connector last observed this price (UTC).")

    @classmethod
    def from_row(cls, row: OfferRow) -> OfferOut:
        return cls(
            offer_id=row.offer_id,
            supplier_account_id=row.supplier_account_id,
            supplier_product_id=row.supplier_product_id,
            price=f"{row.price:.4f}",
            currency=row.currency,
            price_uah=f"{row.price_uah:.4f}" if row.price_uah is not None else None,
            rrp_uah=f"{row.rrp_uah:.4f}" if row.rrp_uah is not None else None,
            observed_at=row.observed_at.isoformat(),
        )
