"""Smoke test: bootstrap a real FastAPI app offline and exercise the baseline it wires."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sa_core.errors import NotFoundError
from sa_observability import bootstrap


def test_bootstrap__wires_health_errors_and_boots() -> None:
    app = FastAPI()
    registry = bootstrap(app, service_name="catalog", env="dev")  # no OTLP endpoint
    registry.add("db", lambda: True)

    @app.get("/boom")
    async def boom() -> None:
        raise NotFoundError("nope")

    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/healthz").json() == {"status": "ok"}

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["checks"] == {"db": True}

    problem = client.get("/boom")
    assert problem.status_code == 404
    assert problem.headers["content-type"].startswith("application/problem+json")
    assert problem.json()["detail"] == "nope"
