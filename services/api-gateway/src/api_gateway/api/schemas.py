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
