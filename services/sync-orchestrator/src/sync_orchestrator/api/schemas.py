"""API response models with LLM-quality field descriptions (AI-ready, hard rule 7).

Operational fields only — never the account's ``credentials_ref`` or financial terms
(``settlement_currency``), per hard rule 6.
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


class SyncAccountOut(BaseModel):
    """Sync status of one scheduled account (operational fields only)."""

    account_id: str = Field(description="Account ULID being synced.")
    supplier_code: str = Field(description="Supplier the account belongs to, e.g. 'brain'.")
    kind: str = Field(description="What is synced: products | offers | all.")
    mode: str = Field(description="Sync mode: full | delta.")
    interval_seconds: float = Field(description="Minimum seconds between scheduled syncs.")
    last_requested_at: str | None = Field(
        default=None, description="When a sync was last requested for this account (ISO-8601 UTC)."
    )
    next_due_at: str | None = Field(
        default=None, description="When the next scheduled sync is due (ISO-8601 UTC)."
    )
    status: str = Field(description="Derived health: 'never' | 'ok' | 'overdue'.")


class TriggerResultOut(BaseModel):
    """Outcome of a manual sync request."""

    account_id: str = Field(description="Account the sync was requested for.")
    sync_job_id: str = Field(description="ULID of the emitted sync job.")
    requested_at: str = Field(description="When the sync was requested (ISO-8601 UTC).")
