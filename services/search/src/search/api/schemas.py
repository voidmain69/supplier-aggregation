"""API models with LLM-quality field descriptions (AI-ready, hard rule 7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from search.adapters.models import SearchDocumentRow


class Problem(BaseModel):
    """RFC 9457 problem+json error body (returned on 4xx/5xx)."""

    type: str = Field(description="Stable URI identifying the error type.")
    title: str = Field(description="Short, human-readable summary of the error type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(description="Human/LLM-readable explanation with a next step.")
    instance: str | None = Field(default=None, description="URI of the specific occurrence.")
    trace_id: str | None = Field(default=None, description="Trace id to correlate with telemetry.")


class SearchRequest(BaseModel):
    """A lexical search query. Every token must appear in a product's name/brand/code/articul."""

    query: str = Field(
        description="Free-text query, e.g. 'asus b850 wifi'. Tokenized; all tokens must match.",
        min_length=1,
    )
    cursor: str | None = Field(
        default=None, description="Opaque cursor from a previous response's next_cursor."
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max hits per page (1-100).")


class SemanticSearchRequest(BaseModel):
    """A natural-language search query, matched by meaning over product embeddings."""

    query: str = Field(
        description="Natural-language need, e.g. 'motherboard for Ryzen 9000 with Wi-Fi 7'.",
        min_length=1,
    )
    limit: int = Field(default=20, ge=1, le=100, description="Max hits to return (1-100).")


class SearchHit(BaseModel):
    """One matching product. ``score`` is set for semantic results (cosine similarity, 0-1)."""

    supplier_product_id: str = Field(description="Internal id (ULID) of the matched product.")
    supplier_code: str = Field(description="Supplier the product belongs to, e.g. 'brain'.")
    name: str = Field(description="Product name.")
    brand: str | None = Field(default=None, description="Brand, if known.")
    articul: str | None = Field(default=None, description="Supplier articul, if any.")
    external_code: str | None = Field(default=None, description="Supplier product code, if any.")
    gtin: str | None = Field(
        default=None, description="Normalized GTIN-14, if the product has one."
    )
    score: float | None = Field(
        default=None,
        description="Semantic similarity in [0,1] (higher is closer); null for lexical hits.",
    )

    @classmethod
    def from_row(cls, row: SearchDocumentRow, *, score: float | None = None) -> SearchHit:
        return cls(
            supplier_product_id=row.supplier_product_id,
            supplier_code=row.supplier_code,
            name=row.name,
            brand=row.brand,
            articul=row.articul,
            external_code=row.external_code,
            gtin=row.gtin,
            score=score,
        )
