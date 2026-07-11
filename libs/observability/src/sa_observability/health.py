"""Liveness and readiness endpoints.

``/healthz`` is a dependency-free liveness probe. ``/readyz`` runs the registered
readiness checks (DB, broker, …) and returns 503 with per-check detail if any fails, so
Kubernetes only routes traffic to a pod once its dependencies are reachable.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse

ReadinessCheck = Callable[[], bool | Awaitable[bool]]


class HealthRegistry:
    """A named set of readiness checks evaluated by ``/readyz``."""

    def __init__(self) -> None:
        self._checks: dict[str, ReadinessCheck] = {}

    def add(self, name: str, check: ReadinessCheck) -> None:
        """Register a readiness check; ``check`` may be sync or async and returns bool."""
        self._checks[name] = check

    async def run(self) -> dict[str, bool]:
        """Evaluate all checks; a raised exception counts as a failed check."""
        results: dict[str, bool] = {}
        for name, check in self._checks.items():
            try:
                outcome = check()
                results[name] = await outcome if inspect.isawaitable(outcome) else bool(outcome)
            except Exception:
                results[name] = False
        return results


def add_health_routes(app: FastAPI, registry: HealthRegistry) -> None:
    """Attach ``/healthz`` and ``/readyz`` to the app."""

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> JSONResponse:
        results = await registry.run()
        ready = all(results.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ok" if ready else "unavailable", "checks": results},
        )
