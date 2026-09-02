"""
OpenTelemetry-backed Observability Adapter (skeleton)

This is a PoC skeleton that attempts to import OpenTelemetry SDK modules. If the SDK
is not available, it falls back to NoopAdapter. The implementation below deliberately
keeps SDK usage inside the implementation so Core never imports OpenTelemetry types.

DO NOT enable this adapter in production until license/SCA review and configuration
are approved.
"""
import logging
from typing import Any, Dict, Optional

from .observability_adapter import ObservabilityAdapter, SpanHandle

logger = logging.getLogger("liuhao.observability.opentelemetry")

try:
    # Import lazily — if opentelemetry packages are not installed, fallback to noop
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    OTEL_AVAILABLE = True
except Exception as e:
    logger.warning("OpenTelemetry not available: %s", e)
    OTEL_AVAILABLE = False


class OpenTelemetryAdapter(ObservabilityAdapter):
    def __init__(self):
        self._initialized = False
        self._tracer = None

    def init(self, config: Dict[str, Any]) -> None:
        if not OTEL_AVAILABLE:
            raise RuntimeError("OpenTelemetry SDK not installed")
        # Minimal init; real implementation must configure resource, sampler, exporters
        resource = Resource.create({"service.name": config.get("service_name", "liuhao")})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=config.get("otlp_endpoint"))
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(__name__)
        self._initialized = True
        logger.info("OpenTelemetryAdapter initialized")

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> SpanHandle:
        if not self._initialized:
            raise RuntimeError("Adapter not initialized")
        span = self._tracer.start_span(name, attributes=attributes)
        return SpanHandle(span)

    def end_span(self, span: SpanHandle, attributes: Optional[Dict[str, Any]] = None) -> None:
        if getattr(span, "_internal", None) is not None:
            span_handle = span._internal
            for k, v in (attributes or {}).items():
                span_handle.set_attribute(k, v)
            span_handle.end()

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        # Metrics API usage omitted in this skeleton; real impl should use MeterProvider
        logger.debug(f"record_metric {name}={value} labels={labels}")

    def inject_context(self, carrier: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> None:
        # Use propagation.inject in real impl
        logger.debug("inject_context (skeleton)")

    def extract_context(self, carrier: Dict[str, str]) -> Optional[Dict[str, Any]]:
        logger.debug("extract_context (skeleton)")
        return None

    def shutdown(self, timeout: Optional[int] = None) -> None:
        logger.info("OpenTelemetryAdapter shutdown")
