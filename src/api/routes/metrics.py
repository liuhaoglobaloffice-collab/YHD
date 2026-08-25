"""
Prometheus exposition endpoint for provider metrics (text/plain).
Reads in-memory metrics from src.api.providers_metrics.get_latest_metrics and exposes
simple gauges:
- provider_model_latency_ms{provider="",model=""}
- provider_model_success_rate{provider="",model=""}
- provider_model_samples_total{provider="",model=""}

This is intentionally lightweight and scrapes the in-memory store; for production
use, hook Prometheus to a proper exporter or write samples to a TSDB.
"""
from fastapi import APIRouter, Response
from typing import List

from src.api.providers_metrics import get_latest_metrics

router = APIRouter(prefix="", tags=["metrics"])


@router.get("/metrics")
async def prometheus_metrics():
    # get latest metrics shaped as list of dicts: {provider, model, points: [{timestamp, latency_ms, success_rate}, ...]}
    data = get_latest_metrics(samples=12)

    lines: List[str] = []
    # help/TYPE lines
    lines.append('# HELP provider_model_latency_ms Latency in milliseconds for provider-model samples')
    lines.append('# TYPE provider_model_latency_ms gauge')
    lines.append('# HELP provider_model_success_rate Success rate for provider-model samples (0..1)')
    lines.append('# TYPE provider_model_success_rate gauge')
    lines.append('# HELP provider_model_samples_total Number of samples in the store for provider-model')
    lines.append('# TYPE provider_model_samples_total gauge')

    for item in data:
        prov = item.get('provider')
        model = item.get('model')
        pts = item.get('points', [])
        samples = len(pts)
        if samples == 0:
            continue
        # expose latest latency and success as gauges and a sample count
        latest = pts[-1]
        latency = latest.get('latency_ms', 0)
        success = latest.get('success_rate', 0.0)
        labels = f'provider="{prov}",model="{model}"'
        lines.append(f'provider_model_latency_ms{{{labels}}} {latency}')
        lines.append(f'provider_model_success_rate{{{labels}}} {success}')
        lines.append(f'provider_model_samples_total{{{labels}}} {samples}')

    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")
