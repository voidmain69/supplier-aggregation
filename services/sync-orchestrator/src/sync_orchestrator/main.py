"""API entry point (uvicorn factory). The scheduling work runs in the separate
``sync_orchestrator.scheduler`` and ``sync_orchestrator.relay`` processes; the HTTP surface
here is just the operational baseline (health, telemetry) from ``sa_observability.bootstrap``.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from sa_observability import bootstrap
from sync_orchestrator.api.routes import router
from sync_orchestrator.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="sync-orchestrator",
        version="0.1.0",
        description=(
            "Schedules supplier syncs. On a per-account interval it emits sync.job.requested "
            "so the owning connector fetches fresh catalog/prices — the source of the ingestion "
            "pipeline. Also exposes sync status + a manual trigger for the operator dashboard."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    app.state.settings = settings
    bootstrap(
        app,
        service_name="sync-orchestrator",
        env=settings.env,
        otlp_endpoint=settings.otlp_endpoint,
    )
    app.include_router(router)
    return app
