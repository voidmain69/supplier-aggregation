"""ASGI entry point: the MCP streamable-HTTP app plus a health route.

The gateway is an MCP server (not a REST service), so there is no OpenAPI surface — agents
discover its tools via MCP. Structured logging and tracing are configured directly (the
FastAPI-specific ``bootstrap`` does not apply to a Starlette/MCP app).
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_gateway.server import build_server
from mcp_gateway.settings import Settings
from sa_observability import configure_logging, setup_telemetry


async def _healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def create_app() -> Starlette:
    settings = Settings()
    configure_logging(service="mcp-gateway", env=settings.env)
    setup_telemetry(service="mcp-gateway", env=settings.env, otlp_endpoint=settings.otlp_endpoint)
    app: Starlette = build_server(settings).streamable_http_app()
    app.add_route("/healthz", _healthz, methods=["GET"], include_in_schema=False)
    return app
