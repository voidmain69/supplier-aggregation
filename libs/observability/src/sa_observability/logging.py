"""structlog configuration: JSON in prod, console in dev, with trace correlation.

Every log line carries ``service``, ``env``, ``level``, an ISO-8601 UTC ``timestamp`` and,
when emitted inside a span, ``trace_id``/``span_id`` for log↔trace correlation. Sensitive
fields are redacted (see :mod:`sa_observability.sanitizer`). Services never configure
logging by hand — :func:`sa_observability.bootstrap.bootstrap` calls this.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from opentelemetry import trace
from structlog.typing import EventDict, WrappedLogger

from sa_observability.sanitizer import DEFAULT_SENSITIVE_KEYS, redacting_processor


def _add_trace_context(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def configure_logging(
    *,
    service: str,
    env: str,
    level: str = "INFO",
    json_output: bool | None = None,
) -> None:
    """Configure structlog process-wide. ``json_output`` defaults to True outside dev."""
    if json_output is None:
        json_output = env != "dev"

    def _add_context(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", service)
        event_dict.setdefault("env", env)
        return event_dict

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_context,
            _add_trace_context,
            redacting_processor(DEFAULT_SENSITIVE_KEYS),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)
