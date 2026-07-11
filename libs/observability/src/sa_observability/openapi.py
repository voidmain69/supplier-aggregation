"""AI-ready OpenAPI hardening shared by every service (hard rule 7 / .spectral.yaml).

Post-processes FastAPI's generated schema so it always: declares a bearer security scheme
and applies it per-operation, renders every 4xx/5xx response as ``application/problem+json``
(RFC 9457), and carries servers/contact/tags. :func:`sa_observability.bootstrap.bootstrap`
wires this in, so services get a compliant ``/openapi.json`` for free.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

_CONTACT = {"name": "Supplier Aggregation Platform", "email": "Info_DIT@erc.ua"}
_SECURITY: list[dict[str, list[str]]] = [{"bearerAuth": []}]
_HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def build_openapi(app: FastAPI) -> dict[str, Any]:
    """Build (and cache) the hardened OpenAPI schema for ``app``."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact=_CONTACT,
    )
    schema["servers"] = [{"url": "/", "description": "This service (behind the API gateway)."}]
    components = schema.setdefault("components", {})
    components.setdefault("securitySchemes", {})["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "description": "Service API key or OIDC token, issued/validated by the API gateway.",
    }

    tags: set[str] = set()
    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            operation["security"] = _SECURITY
            tags.update(operation.get("tags", []))
            for code, response in operation.get("responses", {}).items():
                if code[:1] in {"4", "5"} and "content" in response:
                    content = response["content"]
                    if "application/json" in content:
                        content["application/problem+json"] = content.pop("application/json")

    if tags:
        schema["tags"] = [{"name": name} for name in sorted(tags)]

    app.openapi_schema = schema
    return schema
