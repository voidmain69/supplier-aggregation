"""CORS: a browser SPA (curation-ui) on an allowed origin gets the right preflight headers."""

from __future__ import annotations

import httpx
import pytest
from api_gateway.main import create_app

_ORIGIN = "http://localhost:5173"


@pytest.fixture
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_GATEWAY_CORS_ALLOW_ORIGINS", f'["{_ORIGIN}"]')


async def test_preflight__allowed_origin_gets_cors_headers(_configured: None) -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway.test"
    ) as c:
        resp = await c.options(
            "/v1/curation/queue",
            headers={
                "Origin": _ORIGIN,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
    assert resp.headers["access-control-allow-origin"] == _ORIGIN
    assert "GET" in resp.headers["access-control-allow-methods"]


async def test_preflight__unknown_origin_is_not_allowed(_configured: None) -> None:
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway.test"
    ) as c:
        resp = await c.options(
            "/v1/curation/queue",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" not in resp.headers


async def test_no_cors_configured__no_cors_headers() -> None:
    # Default settings (empty allowlist) must not add the middleware at all.
    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway.test"
    ) as c:
        resp = await c.options(
            "/v1/curation/queue",
            headers={"Origin": _ORIGIN, "Access-Control-Request-Method": "GET"},
        )
    assert "access-control-allow-origin" not in resp.headers
