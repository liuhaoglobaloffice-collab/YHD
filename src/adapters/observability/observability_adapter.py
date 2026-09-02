"""
Observability Adapter contract for LiuHao-AI-OS

This module defines the adapter interface that Core will import/use. Implementations must
live behind this interface and Core MUST NOT import any vendor-specific SDKs.

This is a PLAN-only skeleton. Do not modify Core to import this file until the adapter
and its CI/SCA checks are approved.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class SpanHandle:
    """Opaque span handle returned by start_span"""
    def __init__(self, _internal: Any = None):
        self._internal = _internal

class ObservabilityAdapter(ABC):
    @abstractmethod
    def init(self, config: Dict[str, Any]) -> None:
        """Initialize the adapter (may raise on fatal misconfig)"""
        raise NotImplementedError()

    @abstractmethod
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> SpanHandle:
        raise NotImplementedError()

    @abstractmethod
    def end_span(self, span: SpanHandle, attributes: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError()

    @abstractmethod
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        raise NotImplementedError()

    @abstractmethod
    def inject_context(self, carrier: Dict[str, str], context: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError()

    @abstractmethod
    def extract_context(self, carrier: Dict[str, str]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError()

    @abstractmethod
    def shutdown(self, timeout: Optional[int] = None) -> None:
        raise NotImplementedError()


def noop_adapter_factory():
    from .noop_adapter import NoopAdapter
    return NoopAdapter()
