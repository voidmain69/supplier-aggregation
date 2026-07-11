"""OpenTelemetry tracer/meter provider setup.

Providers export via OTLP to the collector when an endpoint is configured; with no
endpoint (e.g. unit tests) they are created without exporters so instrumentation is inert
but the API still works. ``deployment.environment`` and ``service.name`` are attached as
resource attributes so every span/metric is attributable to a service and environment.
"""

from __future__ import annotations

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(*, service: str, env: str, otlp_endpoint: str | None = None) -> None:
    """Install global tracer and meter providers for a service."""
    resource = Resource.create({"service.name": service, "deployment.environment": env})

    tracer_provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True))
        )
    trace.set_tracer_provider(tracer_provider)

    readers: list[MetricReader] = []
    if otlp_endpoint:
        readers.append(
            PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True))
        )
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))


def current_trace_id() -> str | None:
    """Return the active trace id as a 32-char hex string, or None outside a span."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        return format(span_context.trace_id, "032x")
    return None
