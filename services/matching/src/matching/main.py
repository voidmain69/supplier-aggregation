"""API entry point (uvicorn factory). The event consumer is a separate process — see
``matching.consumer``. AI-ready OpenAPI is applied by ``sa_observability.bootstrap``.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from matching.api.routes import router
from matching.settings import Settings
from sa_observability import bootstrap


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="matching",
        version="0.1.0",
        description=(
            "Matching service. Links supplier products to canonical products (GTIN auto + "
            "operator curation) and serves the canonical catalog."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    bootstrap(app, service_name="matching", env=settings.env, otlp_endpoint=settings.otlp_endpoint)
    app.include_router(router)
    return app
