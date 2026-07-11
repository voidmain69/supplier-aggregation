"""sa_observability — OTel + structlog baseline every service shares.

One call — :func:`bootstrap` — gives a FastAPI service structured logging with secret
redaction and trace correlation, OTel tracing/metrics, RFC 9457 error handling, and
health/readiness probes.
"""

from __future__ import annotations

from sa_observability.bootstrap import bootstrap
from sa_observability.health import HealthRegistry
from sa_observability.logging import configure_logging, get_logger
from sa_observability.sanitizer import DEFAULT_SENSITIVE_KEYS, redact
from sa_observability.tracing import current_trace_id, setup_telemetry

__all__ = [
    "DEFAULT_SENSITIVE_KEYS",
    "HealthRegistry",
    "bootstrap",
    "configure_logging",
    "current_trace_id",
    "get_logger",
    "redact",
    "setup_telemetry",
]
