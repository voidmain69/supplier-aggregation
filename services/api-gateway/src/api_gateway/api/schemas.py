"""Gateway response models. Read/curation payloads are relayed verbatim from downstream
services (which already carry LLM-quality field descriptions), so the only model the gateway
declares itself is the shared RFC 9457 error body.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class CreateCanonicalIn(BaseModel):
    """Fields for a brand-new canonical product created from a curation item (mirrors matching)."""

    title: str = Field(
        min_length=1, description="Canonical title for the new product; prefill from the supplier."
    )
    brand: str | None = Field(default=None, description="Brand/vendor name, if known.")
    gtin: str | None = Field(
        default=None,
        description="Normalized GTIN-14 to assign; must not already belong to another canonical.",
    )


class MergeCanonicalIn(BaseModel):
    """Which canonical to fold into the target (mirrors matching)."""

    source_canonical_product_id: str = Field(
        description="The canonical to merge FROM; it is removed and its links move to the target."
    )
