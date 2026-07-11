from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sa_core.errors import NotFoundError, RateLimitedError
from sa_observability.errors import install_error_handlers


def _client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("no such offer", instance="/missing")

    @app.get("/slow")
    async def slow() -> None:
        raise RateLimitedError("slow down", retry_after_seconds=7)

    @app.get("/items/{item_id}")
    async def item(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    return TestClient(app, raise_server_exceptions=False)


def test_app_error__renders_problem_json() -> None:
    resp = _client().get("/missing")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    body = resp.json()
    assert body["type"].endswith("/not-found")
    assert body["detail"] == "no such offer"
    assert body["instance"] == "/missing"


def test_rate_limited__sets_retry_after_header() -> None:
    resp = _client().get("/slow")
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == "7"


def test_request_validation__becomes_422_problem() -> None:
    resp = _client().get("/items/not-an-int")
    assert resp.status_code == 422
    body = resp.json()
    assert body["type"].endswith("/validation-error")
    assert body["errors"][0]["type"] == "int_parsing"
