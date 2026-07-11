"""API entry point (uvicorn factory). The event consumer is a separate process — see
``offer.consumer``. Building the engine here does not open a connection; it is used lazily
per request. AI-ready OpenAPI is applied by ``sa_observability.bootstrap``.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from offer.api.routes import router
from offer.settings import Settings
from sa_observability import bootstrap


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="offer",
        version="0.1.0",
        description=(
            "Offer service. Owns supplier offers (prices/availability per account), "
            "ingested from events. Query offers for a product or the cheapest offer."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    bootstrap(app, service_name="offer", env=settings.env, otlp_endpoint=settings.otlp_endpoint)
    app.include_router(router)
    return app
