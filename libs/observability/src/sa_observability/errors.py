"""FastAPI exception handlers producing RFC 9457 problem+json.

Wired by :func:`sa_observability.bootstrap.bootstrap` so every service maps its
:class:`sa_core.errors.AppError` hierarchy and request-validation failures to the same
``application/problem+json`` shape, complete with the active ``trace_id``.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sa_core.errors import AppError, RateLimitedError, ValidationError
from sa_observability.tracing import current_trace_id

PROBLEM_JSON = "application/problem+json"


def _problem_response(exc: AppError, request: Request) -> JSONResponse:
    problem = exc.to_problem(trace_id=current_trace_id())
    problem.setdefault("instance", str(request.url.path))
    headers: dict[str, str] = {}
    if isinstance(exc, RateLimitedError) and exc.retry_after_seconds is not None:
        headers["Retry-After"] = str(exc.retry_after_seconds)
    return JSONResponse(
        status_code=exc.http_status,
        content=problem,
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def install_error_handlers(app: FastAPI) -> None:
    """Register problem+json handlers for AppError and request validation errors."""

    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _problem_response(exc, request)

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Keep only JSON-safe fields; raw errors() may embed exception objects in ctx.
        errors = [
            {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
            for err in exc.errors()
        ]
        wrapped = ValidationError(
            "Request failed validation; check the listed fields and retry.",
            extra={"errors": errors},
        )
        return _problem_response(wrapped, request)
