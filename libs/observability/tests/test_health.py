from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sa_observability.health import HealthRegistry, add_health_routes


def test_healthz__always_ok() -> None:
    app = FastAPI()
    add_health_routes(app, HealthRegistry())
    resp = TestClient(app).get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz__all_checks_pass() -> None:
    app = FastAPI()
    registry = HealthRegistry()
    registry.add("db", lambda: True)

    async def broker() -> bool:
        return True

    registry.add("broker", broker)
    add_health_routes(app, registry)

    resp = TestClient(app).get("/readyz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "checks": {"db": True, "broker": True}}


def test_readyz__failing_check__returns_503() -> None:
    app = FastAPI()
    registry = HealthRegistry()
    registry.add("db", lambda: True)
    registry.add("broker", lambda: False)
    add_health_routes(app, registry)

    resp = TestClient(app).get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["checks"] == {"db": True, "broker": False}


def test_readyz__raising_check__counts_as_failed() -> None:
    app = FastAPI()
    registry = HealthRegistry()

    def boom() -> bool:
        raise RuntimeError("connection refused")

    registry.add("db", boom)
    add_health_routes(app, registry)

    resp = TestClient(app).get("/readyz")
    assert resp.status_code == 503
    assert resp.json()["checks"] == {"db": False}
