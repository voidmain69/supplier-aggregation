"""Application error hierarchy mapped to RFC 9457 problem+json.

Every service raises these on its API boundary; a single FastAPI exception handler
turns them into `application/problem+json` responses with an actionable ``detail`` and
a stable ``type`` URI (see docs/standards/api-guidelines.md). Keeping the mapping here
means the error contract is identical across all services.
"""

from __future__ import annotations

from typing import Any

_TYPE_BASE = "https://errors.sa.internal"


class AppError(Exception):
    """Base class for all domain/application errors.

    Subclasses set ``code`` (stable slug, becomes the problem ``type``), ``http_status``
    and ``title``. ``detail`` should tell the caller — human or LLM — what to do next.
    """

    code: str = "internal-error"
    http_status: int = 500
    title: str = "Internal Server Error"

    def __init__(
        self,
        detail: str,
        *,
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.instance = instance
        self.extra = extra or {}

    def to_problem(self, *, trace_id: str | None = None) -> dict[str, Any]:
        """Render an RFC 9457 problem+json body."""
        problem: dict[str, Any] = {
            "type": f"{_TYPE_BASE}/{self.code}",
            "title": self.title,
            "status": self.http_status,
            "detail": self.detail,
        }
        if self.instance is not None:
            problem["instance"] = self.instance
        if trace_id is not None:
            problem["trace_id"] = trace_id
        problem.update(self.extra)
        return problem


class NotFoundError(AppError):
    code = "not-found"
    http_status = 404
    title = "Not Found"


class ValidationError(AppError):
    code = "validation-error"
    http_status = 422
    title = "Unprocessable Entity"


class ConflictError(AppError):
    code = "conflict"
    http_status = 409
    title = "Conflict"


class RateLimitedError(AppError):
    code = "rate-limited"
    http_status = 429
    title = "Too Many Requests"

    def __init__(
        self,
        detail: str,
        *,
        retry_after_seconds: int | None = None,
        instance: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail, instance=instance, extra=extra)
        self.retry_after_seconds = retry_after_seconds


class UpstreamError(AppError):
    """A supplier or downstream dependency failed or misbehaved."""

    code = "upstream-error"
    http_status = 502
    title = "Bad Gateway"
