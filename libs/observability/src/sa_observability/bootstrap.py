"""One-call observability wiring for a service.

``bootstrap(app, service_name=...)`` configures structlog, installs OTel tracer/meter
providers, instruments FastAPI (and httpx if present), registers RFC 9457 error handlers,
and mounts ``/healthz`` + ``/readyz``. Services call this in their app factory and get the
full platform baseline for free.
"""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from sa_observability.errors import install_error_handlers
from sa_observability.health import HealthRegistry, add_health_routes
from sa_observability.logging import configure_logging, get_logger
from sa_observability.tracing import setup_telemetry


def bootstrap(
    app: FastAPI,
    *,
    service_name: str,
    env: str = "dev",
    otlp_endpoint: str | None = None,
    log_level: str = "INFO",
    health: HealthRegistry | None = None,
) -> HealthRegistry:
    """Wire logging, tracing/metrics, error handling and health probes into ``app``.

    Returns the :class:`HealthRegistry` so the caller can register readiness checks
    (``registry.add("postgres", ...)``). Idempotent enough for tests: global providers
    are set once and re-instrumentation of the same app is a no-op.
    """
    configure_logging(service=service_name, env=env, level=log_level)
    setup_telemetry(service=service_name, env=env, otlp_endpoint=otlp_endpoint)

    FastAPIInstrumentor.instrument_app(app)
    try:  # httpx is optional — only services that make HTTP calls depend on it
        from opentelemetry.instrumentation.httpx import (  # noqa: PLC0415 -- optional dep
            HTTPXClientInstrumentor,
        )

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

    install_error_handlers(app)
    registry = health or HealthRegistry()
    add_health_routes(app, registry)

    get_logger(__name__).info("observability_bootstrapped", service=service_name, env=env)
    return registry
