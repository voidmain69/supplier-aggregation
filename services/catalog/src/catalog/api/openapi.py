"""OpenAPI hardening so the schema meets the platform's AI-ready rules (.spectral.yaml).

FastAPI's generated schema is post-processed to: declare a bearer security scheme and
apply it per-operation, and render every 4xx/5xx response as ``application/problem+json``
(RFC 9457). Runtime ``/openapi.json`` and the exported file share this one code path.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

_SECURITY: list[dict[str, list[str]]] = [{"bearerAuth": []}]


def build_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact={"name": "Supplier Aggregation Platform", "email": "Info_DIT@erc.ua"},
        tags=[
            {
                "name": "supplier-products",
                "description": "Supplier products ingested by the catalog.",
            }
        ],
    )
    schema["servers"] = [{"url": "/", "description": "This service (behind the API gateway)."}]
    components = schema.setdefault("components", {})
    components.setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "description": "Service API key or OIDC token, issued/validated by the API gateway.",
    }

    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            operation["security"] = _SECURITY
            for code, response in operation.get("responses", {}).items():
                if code[:1] in {"4", "5"} and "content" in response:
                    content = response["content"]
                    if "application/json" in content:
                        content["application/problem+json"] = content.pop("application/json")

    app.openapi_schema = schema
    return schema
