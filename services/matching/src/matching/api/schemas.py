"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from matching.adapters.models import CanonicalProductRow, DecisionLogRow


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


class CurationItemOut(BaseModel):
    """A supplier→canonical link awaiting an operator decision."""

    supplier_product_id: str = Field(description="The supplier product to be matched (ULID).")
    canonical_product_id: str = Field(
        description="The suggested canonical product (an existing one, or a fresh draft)."
    )
    method: str = Field(description="How the candidate was produced (e.g. 'rag_suggested').")
    confidence: float = Field(description="Candidate score in [0,1]; higher = stronger match.")
    status: str = Field(description="Link status; items in the queue are 'pending_review'.")


class LinkDecisionOut(BaseModel):
    """Result of confirming or rejecting a curation item."""

    supplier_product_id: str = Field(description="The supplier product that was decided.")
    canonical_product_id: str = Field(description="The canonical product it maps to.")
    status: str = Field(description="New link status: 'confirmed' or 'rejected'.")


class CreateCanonicalIn(BaseModel):
    """Fields for a brand-new canonical product created from a curation item.

    Use this when the suggested candidate is wrong AND the supplier product is a genuinely new
    product (not yet in the catalog). Prefill from the supplier product; the operator may edit.
    """

    title: str = Field(
        min_length=1,
        description="Canonical title for the new product, e.g. 'Acme Widget Pro 2000'.",
    )
    brand: str | None = Field(default=None, description="Brand/vendor name, if known.")
    gtin: str | None = Field(
        default=None,
        description=(
            "Normalized GTIN-14 to assign, if the product carries one. Must not already belong "
            "to another canonical (that would be a match, not a new product)."
        ),
    )


class MergeCanonicalIn(BaseModel):
    """Which canonical to fold into the target (all its links move to the target)."""

    source_canonical_product_id: str = Field(
        description="The canonical to merge FROM; it is removed and its links move to the target."
    )


class MergeResultOut(BaseModel):
    """Outcome of merging one canonical product into another."""

    target_canonical_product_id: str = Field(description="The surviving canonical product.")
    source_canonical_product_id: str = Field(description="The merged-away canonical (now removed).")
    moved_links: int = Field(description="How many supplier-product links were repointed.")


class DecisionOut(BaseModel):
    """One immutable entry in the curation decision journal (audit log)."""

    decision_id: str = Field(description="ULID of this decision (also the time-ordering key).")
    action: str = Field(description="What was decided: confirm | reject | create_new | merge.")
    supplier_product_id: str | None = Field(
        default=None, description="The supplier product decided (null for a merge)."
    )
    canonical_product_id: str = Field(description="The canonical product the decision resolved to.")
    method: str | None = Field(default=None, description="Match method, if applicable.")
    confidence: float | None = Field(
        default=None, description="Candidate confidence in [0,1], if applicable."
    )
    operator: str = Field(description="Who decided (operator id, or 'system' / 'operator').")
    note: str | None = Field(default=None, description="Human-readable context, if any.")
    decided_at: str = Field(description="When the decision was made (ISO-8601 UTC).")

    @classmethod
    def from_row(cls, row: DecisionLogRow) -> DecisionOut:
        return cls(
            decision_id=row.decision_id,
            action=row.action,
            supplier_product_id=row.supplier_product_id,
            canonical_product_id=row.canonical_product_id,
            method=row.method,
            confidence=row.confidence,
            operator=row.operator,
            note=row.note,
            decided_at=row.decided_at.isoformat(),
        )
