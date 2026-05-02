from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


@dataclass(slots=True)
class TelemetryRuntime:
    enabled: bool
    tracer_provider: TracerProvider | None = None
    meter_provider: MeterProvider | None = None

    def shutdown(self) -> None:
        if self.meter_provider is not None:
            self.meter_provider.shutdown()
        if self.tracer_provider is not None:
            self.tracer_provider.shutdown()


def configure_observability(
    app: FastAPI,
    *,
    enabled: bool,
    service_name: str,
) -> TelemetryRuntime:
    """Configure OTLP tracing/metrics using standard OpenTelemetry env vars."""
    if not enabled:
        return TelemetryRuntime(enabled=False)

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "web-log-analyzer",
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        excluded_urls=r"/health/.*",
        http_capture_headers_sanitize_fields=[
            "authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
        ],
    )

    return TelemetryRuntime(
        enabled=True,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
