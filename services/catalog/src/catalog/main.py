"""API entry point (uvicorn factory). The event consumer is a separate process — see
``catalog.consumer``. Building the engine here does not open a connection; it is used
lazily per request.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from catalog.api.routes import canonical_router, router
from catalog.settings import Settings
from sa_observability import bootstrap


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="catalog",
        version="0.1.0",
        description=(
            "Catalog service. Owns supplier products (ingested from events) and the "
            "canonical catalog. Query it for products by supplier, code or GTIN."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    bootstrap(app, service_name="catalog", env=settings.env, otlp_endpoint=settings.otlp_endpoint)
    app.include_router(router)
    app.include_router(canonical_router)
    return app
