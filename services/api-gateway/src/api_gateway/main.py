"""API entry point (uvicorn factory).

The single authenticated ingress in front of the internal read/curation APIs. It owns no
data: it authenticates and authorizes callers, rate-limits them per principal, and forwards
to the owning service — exposing one aggregated, AI-ready OpenAPI surface.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_gateway.adapters.downstream import Downstream
from api_gateway.api.routes import router
from api_gateway.domain.auth import Principal, StaticPrincipalStore
from api_gateway.domain.rate_limit import RateLimiter
from api_gateway.settings import Settings
from sa_observability import bootstrap


def _principal_store(settings: Settings) -> StaticPrincipalStore:
    return StaticPrincipalStore(
        {
            token_hash: Principal(subject=cfg.subject, scopes=frozenset(cfg.scopes))
            for token_hash, cfg in settings.principals.items()
        }
    )


def create_app() -> FastAPI:
    settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as http:
            app.state.downstream = Downstream(
                http,
                {
                    "catalog": settings.catalog_base_url,
                    "offer": settings.offer_base_url,
                    "price_history": settings.price_history_base_url,
                    "matching": settings.matching_base_url,
                    "sync_orchestrator": settings.sync_orchestrator_base_url,
                },
            )
            yield

    app = FastAPI(
        title="api-gateway",
        version="0.1.0",
        description=(
            "Single authenticated ingress over the platform's internal services. Services and "
            "AI agents call it with a bearer token to read catalog products, offers and price "
            "history, and to curate matches — one consistent, scoped, rate-limited contract."
        ),
        lifespan=lifespan,
    )
    bootstrap(
        app, service_name="api-gateway", env=settings.env, otlp_endpoint=settings.otlp_endpoint
    )
    # A browser SPA (curation-ui) lives on another origin; allow only the configured ones.
    # No wildcard: the gateway is bearer-credentialed. Methods/headers match what the UI sends.
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "traceparent"],
            max_age=600,
        )
    app.state.settings = settings
    app.state.principals = _principal_store(settings)
    app.state.rate_limiter = RateLimiter(
        rate_per_second=settings.rate_limit_per_second, burst=settings.rate_limit_burst
    )
    app.include_router(router)
    return app
