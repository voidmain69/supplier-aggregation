from __future__ import annotations

from connector_brain.main import create_app
from fastapi.testclient import TestClient


def test_create_app__boots_and_serves_health() -> None:
    client = TestClient(create_app())
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200
