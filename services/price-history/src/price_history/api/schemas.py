"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from price_history.adapters.models import PricePointRow


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class PricePointOut(BaseModel):
    """One observed price for an offer at a point in time."""

    offer_id: str = Field(description="The offer this price belongs to (ULID).")
    ts: str = Field(description="When the price was observed (UTC, ISO 8601).")
    price: str = Field(description="Supplier base price (decimal string) in `currency`.")
    currency: str = Field(description="ISO-4217 code of `price`.")
    price_uah: str | None = Field(
        default=None, description="Price in UAH (decimal string), or null. Used for trends."
    )

    @classmethod
    def from_row(cls, row: PricePointRow) -> PricePointOut:
        return cls(
            offer_id=row.offer_id,
            ts=row.ts.isoformat(),
            price=f"{row.price:.4f}",
            currency=row.currency,
            price_uah=f"{row.price_uah:.4f}" if row.price_uah is not None else None,
        )


class PriceStatsOut(BaseModel):
    """Aggregate UAH-price statistics for an offer over a time range."""

    offer_id: str = Field(description="The offer these stats are for (ULID).")
    count: int = Field(description="Number of price points in range.")
    min_uah: str | None = Field(default=None, description="Lowest UAH price seen.")
    max_uah: str | None = Field(default=None, description="Highest UAH price seen.")
    avg_uah: str | None = Field(default=None, description="Average UAH price.")
    last_uah: str | None = Field(default=None, description="Most recent UAH price.")
    last_ts: str | None = Field(default=None, description="Timestamp of the most recent price.")


class DailyPriceStatOut(BaseModel):
    """One day's UAH-price rollup for an offer."""

    day: str = Field(description="Calendar day (UTC, YYYY-MM-DD).")
    count: int = Field(description="Number of price points observed that day.")
    min_uah: str | None = Field(default=None, description="Lowest UAH price that day.")
    max_uah: str | None = Field(default=None, description="Highest UAH price that day.")
    avg_uah: str | None = Field(default=None, description="Average UAH price that day.")
    last_uah: str | None = Field(default=None, description="Last UAH price of the day.")
