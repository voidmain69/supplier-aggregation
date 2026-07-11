from __future__ import annotations

from sa_core.errors import (
    AppError,
    NotFoundError,
    RateLimitedError,
    ValidationError,
)


def test_not_found__problem_json_shape() -> None:
    err = NotFoundError(
        "Offer 01J... does not exist. Use GET /v1/offers?supplier_product_id= to list live offers.",
        instance="/v1/offers/01J",
    )
    problem = err.to_problem(trace_id="4bf92f3577b34da6a3ce929d0e0e4736")
    assert problem == {
        "type": "https://errors.sa.internal/not-found",
        "title": "Not Found",
        "status": 404,
        "detail": err.detail,
        "instance": "/v1/offers/01J",
        "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    }


def test_app_error__is_exception_and_carries_detail() -> None:
    err = ValidationError("bad input")
    assert isinstance(err, AppError)
    assert str(err) == "bad input"
    assert err.http_status == 422


def test_problem__extra_fields_merged() -> None:
    err = ValidationError("bad", extra={"field": "currency"})
    problem = err.to_problem()
    assert problem["field"] == "currency"
    assert "trace_id" not in problem


def test_rate_limited__retry_after_captured() -> None:
    err = RateLimitedError("slow down", retry_after_seconds=3)
    assert err.retry_after_seconds == 3
    assert err.http_status == 429
