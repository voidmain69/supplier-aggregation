"""The aggregated OpenAPI surface stays AI-ready (security, operationIds, problem+json)."""

from __future__ import annotations

from api_gateway.main import create_app

_PRODUCTS = "/v1/products"
_CONFIRM = "/v1/curation/links/{supplier_product_id}/confirm"


def test_openapi__every_operation_declares_security_and_operation_id() -> None:
    schema = create_app().openapi()
    assert "bearerAuth" in schema["components"]["securitySchemes"]

    for path, methods in schema["paths"].items():
        for method, op in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            assert op.get("security") == [{"bearerAuth": []}], f"{method} {path} missing security"
            assert op.get("operationId"), f"{method} {path} missing operationId"


def test_openapi__gateway_errors_are_problem_json() -> None:
    schema = create_app().openapi()
    responses = schema["paths"][_PRODUCTS]["get"]["responses"]
    for code in ("401", "403", "429", "502"):
        assert "application/problem+json" in responses[code]["content"]


def test_openapi__confirm_is_documented_and_mutating() -> None:
    schema = create_app().openapi()
    op = schema["paths"][_CONFIRM]["post"]
    assert op["operationId"] == "confirmCurationLink"
    assert len(op["description"]) >= 40


def test_openapi__no_offset_pagination() -> None:
    schema = create_app().openapi()
    for methods in schema["paths"].values():
        for op in methods.values():
            for param in op.get("parameters", []):
                assert param["name"] != "offset"
