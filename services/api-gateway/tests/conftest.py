from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest
from api_gateway.adapters.downstream import Downstream
from api_gateway.api.deps import get_downstream
from api_gateway.domain.auth import Principal, StaticPrincipalStore, hash_token
from api_gateway.domain.rate_limit import RateLimiter
from api_gateway.main import create_app
from fastapi import FastAPI

TOKEN = "s3cret-test-token"  # dummy credential for tests only
TOKEN_HASH = hash_token(TOKEN)
AUTH = {"Authorization": f"Bearer {TOKEN}"}

_BASE_URLS = {
    "catalog": "http://catalog.test",
    "offer": "http://offer.test",
    "price_history": "http://price-history.test",
    "matching": "http://matching.test",
    "sync_orchestrator": "http://sync-orchestrator.test",
    "search": "http://search.test",
}


class RecordingBackend:
    """A scriptable downstream: records requests, returns a configurable response."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.status = 200
        self.json: Any = {"items": [], "next_cursor": None}
        self.raise_transport = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.raise_transport:
            raise httpx.ConnectError("downstream down", request=request)
        self.requests.append(request)
        if self.status >= 400:
            return httpx.Response(
                self.status,
                json={"type": "x", "title": "t", "status": self.status, "detail": "d"},
                headers={"content-type": "application/problem+json"},
            )
        return httpx.Response(self.status, json=self.json)


@pytest.fixture
def auth() -> dict[str, str]:
    return dict(AUTH)


@pytest.fixture
def backend() -> RecordingBackend:
    return RecordingBackend()


@pytest.fixture
def downstream(backend: RecordingBackend) -> Downstream:
    http = httpx.AsyncClient(transport=httpx.MockTransport(backend.handler))
    return Downstream(http, _BASE_URLS)


AppFactory = Callable[..., FastAPI]


@pytest.fixture
def make_app(downstream: Downstream) -> AppFactory:
    """Build the gateway app with a single test principal holding ``scopes``."""

    def _make(*scopes: str, rate_per_second: float = 1000.0, burst: int = 1000) -> FastAPI:
        app = create_app()
        app.state.principals = StaticPrincipalStore(
            {TOKEN_HASH: Principal(subject="agent:test", scopes=frozenset(scopes))}
        )
        app.state.rate_limiter = RateLimiter(rate_per_second=rate_per_second, burst=burst)
        app.dependency_overrides[get_downstream] = lambda: downstream
        return app

    return _make


@pytest.fixture
def client(make_app: AppFactory) -> Callable[..., httpx.AsyncClient]:
    def _client(*scopes: str, **kwargs: Any) -> httpx.AsyncClient:
        app = make_app(*scopes, **kwargs)
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway.test"
        )

    return _client
