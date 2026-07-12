"""API entry point (uvicorn factory). The event consumer is a separate process — see
``price_history.consumer``. AI-ready OpenAPI is applied by ``sa_observability.bootstrap``.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from price_history.api.routes import router
from price_history.settings import Settings
from sa_observability import bootstrap


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="price-history",
        version="0.1.0",
        description=(
            "Price-history service. Stores every supplier price change as a time series "
            "and serves an offer's history and price stats (min/max/avg/last)."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    bootstrap(
        app, service_name="price-history", env=settings.env, otlp_endpoint=settings.otlp_endpoint
    )
    app.include_router(router)
    return app
