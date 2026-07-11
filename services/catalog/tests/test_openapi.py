from __future__ import annotations

from catalog.main import create_app

_GET_PATH = "/v1/supplier-products/{supplier_product_id}"
_LIST_PATH = "/v1/supplier-products"


def test_openapi__declares_security_scheme_and_per_operation_security() -> None:
    schema = create_app().openapi()
    assert "bearerAuth" in schema["components"]["securitySchemes"]

    get_op = schema["paths"][_GET_PATH]["get"]
    assert get_op["security"] == [{"bearerAuth": []}]
    assert get_op["operationId"] == "getSupplierProduct"


def test_openapi__errors_are_problem_json() -> None:
    schema = create_app().openapi()

    get_404 = schema["paths"][_GET_PATH]["get"]["responses"]["404"]
    assert "application/problem+json" in get_404["content"]

    list_422 = schema["paths"][_LIST_PATH]["get"]["responses"]["422"]
    assert "application/problem+json" in list_422["content"]
    assert "application/json" not in list_422["content"]


def test_openapi__no_offset_pagination_param() -> None:
    schema = create_app().openapi()
    params = schema["paths"][_LIST_PATH]["get"].get("parameters", [])
    assert all(p["name"] != "offset" for p in params)
    assert any(p["name"] == "cursor" for p in params)
