"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from offer.adapters.models import OfferRow
from offer.domain.pricing import FinancialTerms


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
        description="Supplier's raw price converted to UAH (decimal string), or null.",
    )
    effective_price_uah: str | None = Field(
        default=None,
        description=(
            "Comparable UAH price after the account's financial terms (discount, FX, markup). "
            "This is the value offers are ranked by; null if the offer cannot yet be priced in UAH."
        ),
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
            effective_price_uah=(
                f"{row.effective_price_uah:.4f}" if row.effective_price_uah is not None else None
            ),
            rrp_uah=f"{row.rrp_uah:.4f}" if row.rrp_uah is not None else None,
            observed_at=row.observed_at.isoformat(),
        )


class AccountTermsIn(BaseModel):
    """Financial terms to set for a supplier account (operator/admin input, scope-gated)."""

    discount_pct: Decimal = Field(
        default=Decimal(0),
        ge=0,
        lt=1,
        description="Negotiated discount off the base price, as a fraction (0.15 = 15%).",
    )
    markup_pct: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Platform markup added after discount/FX, as a fraction (0.05 = 5%).",
    )
    fx_rate_to_uah: Decimal | None = Field(
        default=None,
        gt=0,
        description=(
            "Multiplier converting the account's settlement currency to UAH. Omit for UAH "
            "accounts; required to price a non-UAH account when the supplier sends no UAH price."
        ),
    )

    def to_terms(self) -> FinancialTerms:
        return FinancialTerms(
            discount_pct=self.discount_pct,
            markup_pct=self.markup_pct,
            fx_rate_to_uah=self.fx_rate_to_uah,
        )


class AccountTermsOut(BaseModel):
    """Confirmation that an account's terms were stored, with the count of re-priced offers."""

    supplier_account_id: str = Field(description="The account whose terms were set.")
    discount_pct: str = Field(description="Stored discount fraction (decimal string).")
    markup_pct: str = Field(description="Stored markup fraction (decimal string).")
    fx_rate_to_uah: str | None = Field(
        default=None, description="Stored FX rate to UAH (decimal string), or null."
    )
    offers_repriced: int = Field(
        description="How many existing offers of this account were re-priced by this change."
    )
