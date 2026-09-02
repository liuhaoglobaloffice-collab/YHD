"""
Noop Observability Adapter

Used when telemetry initialization fails or when Observability is disabled.
No network calls. Stores minimal local logs via Python logging.
"""
import logging
from typing import Any, Dict, Optional
from .observability_adapter import ObservabilityAdapter, SpanHandle

logger = logging.getLogger("liuhao.observability.noop")


class NoopAdapter(ObservabilityAdapter):
    def __init__(self):
        self._initialized = True

    def init(self, config: Dict[str, Any]) -> None:
        logger.warning("NoopAdapter init called — telemetry disabled or failed")
        self._initialized = True

    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> SpanHandle:
        logger.debug(f"noop start_span: {name}")
        return SpanHandle(None)

    def end_span(self, span: SpanHandle, attributes: Optional[Dict[str, Any]] = None) -> None:
        logger.debug("noop end_span")

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        logger.debug(f"noop record_metric: {name}={value} labels={labels}")

    def inject_context(self, carrier: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> None:
        logger.debug("noop inject_context")

    def extract_context(self, carrier: Dict[str, str]) -> Optional[Dict[str, Any]]:
        logger.debug("noop extract_context")
        return None

    def shutdown(self, timeout: Optional[int] = None) -> None:
        logger.debug("noop shutdown")
