"""
Metrics helper enforcing label whitelist and metric types.

This helper is intentionally small and does not depend on any exporter.
"""
import logging
from typing import Dict, Iterable, Mapping

logger = logging.getLogger("liuhao.observability.metrics")

# Default low-cardinality labels allowed
ALLOWED_LABELS = {"service", "component", "model", "provider", "environment"}


def scrub_labels(labels: Mapping[str, str]) -> Dict[str, str]:
    return {k: v for k, v in labels.items() if k in ALLOWED_LABELS}


def record_counter(adapter, name: str, value: float = 1.0, labels: Mapping[str, str] = None):
    labels = labels or {}
    safe = scrub_labels(labels)
    adapter.record_metric(name, value, safe)


def record_gauge(adapter, name: str, value: float, labels: Mapping[str, str] = None):
    labels = labels or {}
    safe = scrub_labels(labels)
    adapter.record_metric(name, value, safe)


def record_histogram(adapter, name: str, value: float, labels: Mapping[str, str] = None):
    labels = labels or {}
    safe = scrub_labels(labels)
    adapter.record_metric(name, value, safe)
