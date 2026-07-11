"""Application entry point. Wire-up only — no business logic here.

The Brain connector is driven by sync jobs (events), not by a consumer-facing REST API,
so the HTTP surface is just the operational baseline (health, telemetry) wired by
``sa_observability.bootstrap``. The event-consumption loop lands in a follow-up increment.
"""

from __future__ import annotations

from fastapi import FastAPI

from connector_brain.settings import Settings
from sa_observability import bootstrap


def create_app() -> FastAPI:
    settings = Settings()
    app = FastAPI(
        title="connector-brain",
        version="0.1.0",
        description=(
            "Brain (api.brain.com.ua) supplier connector. Syncs the Brain catalog, prices "
            "and availability and normalizes them into canonical platform DTOs/events. Not "
            "queried directly by agents — consumer reads go through catalog/offer/search."
        ),
    )
    bootstrap(
        app,
        service_name="connector-brain",
        env=settings.env,
        otlp_endpoint=settings.otlp_endpoint,
    )
    return app
