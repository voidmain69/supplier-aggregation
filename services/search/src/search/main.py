"""API entry point (uvicorn factory). The indexing consumer is a separate process — see
``search.consumer``. Building the engine here does not open a connection; it is used lazily
per request.
"""

from __future__ import annotations

from fastapi import FastAPI
from sa_persistence.db import create_engine, create_session_factory

from sa_observability import bootstrap
from search.api.routes import router
from search.domain.embedding import HashingEmbedder
from search.settings import Settings


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="search",
        version="0.1.0",
        description=(
            "Search service. Find products by free-text query (name/brand/code/articul), by "
            "meaning (natural-language semantic search), or by exact identifier (code, articul, "
            "GTIN). Indexed from supplier product events."
        ),
    )
    app.state.session_factory = create_session_factory(create_engine(settings.db_dsn))
    # Deterministic stand-in embedder; swap a real semantic model here via the Embedder protocol.
    app.state.embedder = HashingEmbedder()
    bootstrap(app, service_name="search", env=settings.env, otlp_endpoint=settings.otlp_endpoint)
    app.include_router(router)
    return app
