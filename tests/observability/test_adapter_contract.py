import pytest
from src.adapters.observability.observability_adapter import ObservabilityAdapter, SpanHandle
from src.adapters.observability.noop_adapter import NoopAdapter


def test_noop_adapter_basic():
    adapter = NoopAdapter()
    adapter.init({})
    span = adapter.start_span("test-span", {"foo": "bar"})
    assert isinstance(span, SpanHandle)
    adapter.end_span(span, {"ended": True})
    adapter.record_metric("test.metric", 1.0, {"service": "test"})
    assert adapter.extract_context({}) is None
    adapter.inject_context({}, None)
    adapter.shutdown()
