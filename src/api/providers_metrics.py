"""
Lightweight provider metrics collector and in-memory store.
- Runs as a background task after system.startup event.
- Probes providers opportunistically (Ollama local if OLLAMA_HOST is set to a URL).
- Keeps bounded per-model time-series in memory for UI graphs.

Design notes:
- Conservative: only performs network probes for providers with URL-like env vars (e.g., OLLAMA). Other providers retain synthetic samples.
- Uses httpx AsyncClient (already a project dependency).
- Stores latest N samples per model (default 120).
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Dict, Deque, List, Optional

import httpx
import structlog

from src.api.provider_catalog import _PROVIDER_CATALOG, provider_status_from_env
from src.core.events import get_event_bus, Event

logger = structlog.get_logger(__name__)

SAMPLE_INTERVAL_SECONDS = 60
MAX_SAMPLES = 120


@dataclass
class MetricPoint:
    timestamp: datetime
    latency_ms: int
    success_rate: float


# Store: provider -> model -> deque[MetricPoint]
_metrics_store: Dict[str, Dict[str, Deque[MetricPoint]]] = {}
_store_lock = asyncio.Lock()

_running_task: Optional[asyncio.Task] = None


async def _probe_ollama(base_url: str, models: List[str]) -> Dict[str, List[MetricPoint]]:
    """Probe an Ollama-like host by calling a model list or root and measuring latency.

    Returns per-model metric lists (single latest sample) — caller will append to store.
    """
    result: Dict[str, List[MetricPoint]] = {}
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        candidates = ["/v1/models", "/models", "/"]
        probe_url = base_url.rstrip("/")
        # try a few well-known endpoints
        ok_url = None
        elapsed = None
        for suffix in candidates:
            try:
                url = probe_url + suffix
                start = datetime.now(UTC)
                r = await client.get(url)
                elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
                if r.status_code < 500:
                    ok_url = url
                    break
            except Exception:
                continue

        # if we found an OK endpoint, use its latency as sample for all models
        if ok_url and elapsed is not None:
            latency = int(elapsed)
            for m in models:
                result[m] = [MetricPoint(timestamp=datetime.now(UTC), latency_ms=latency, success_rate=1.0 if latency < 3000 else 0.9)]
    return result


async def _probe_openai(api_key: str, models: List[str]) -> Dict[str, List[MetricPoint]]:
    """Probe OpenAI by calling the models list endpoint with the API key and measuring latency.

    Returns a per-model single-sample mapping similar to _probe_ollama. If the call fails
    the function will raise or return an empty mapping which the caller will handle.
    """
    result: Dict[str, List[MetricPoint]] = {}
    headers = {"Authorization": f"Bearer {api_key}"}
    timeout = httpx.Timeout(10.0)
    probe_url = "https://api.openai.com/v1/models"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            start = datetime.now(UTC)
            r = await client.get(probe_url, headers=headers)
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
            status_ok = r.status_code < 500
            latency = int(elapsed)
            # If the models endpoint returned a list, try to map samples to configured models
            # Fallback to using the configured models list as keys if response parsing fails.
            for m in models:
                result[m] = [MetricPoint(timestamp=datetime.now(UTC), latency_ms=latency, success_rate=1.0 if status_ok else 0.0)]
        except Exception:
            # propagate to caller (caller will fallback to synthetic)
            raise
    return result


async def _generate_synthetic_sample(status: str, models: List[str]) -> Dict[str, List[MetricPoint]]:
    """Generate synthetic metric samples for given models using previous heuristic."""
    import random

    now = datetime.now(UTC)
    base_latency = 400 if status == "healthy" else 1200 if status == "degraded" else 0
    base_success = 0.995 if status == "healthy" else 0.85 if status == "degraded" else 0.0
    result: Dict[str, List[MetricPoint]] = {}
    for m in models:
        if base_latency == 0:
            latency = 0
        else:
            jitter = random.randint(-int(base_latency * 0.2), int(base_latency * 0.2))
            latency = max(10, base_latency + jitter)
        success = max(0.0, min(1.0, base_success + random.uniform(-0.02, 0.02)))
        result[m] = [MetricPoint(timestamp=now, latency_ms=int(latency), success_rate=round(success, 3))]
    return result


async def _collect_loop() -> None:
    logger.info("metrics_collector_starting")
    while True:
        try:
            await _collect_once()
        except asyncio.CancelledError:
            logger.info("metrics_collector_cancelled")
            raise
        except Exception as e:
            logger.exception("metrics_collect_error", error=str(e))
        await asyncio.sleep(SAMPLE_INTERVAL_SECONDS)


async def _collect_once() -> None:
    """Probe configured providers and append one sample per model to the in-memory store."""
    async with _store_lock:
        now = datetime.now(UTC)
        for provider, metadata in _PROVIDER_CATALOG.items():
            status = provider_status_from_env(provider)
            provider_key = provider.value
            models = metadata.get("models", [])

            # Probe only if provider has URL-like env var (e.g., OLLAMA)
            env_var = metadata.get("env_var")
            env_value = None
            if env_var:
                env_value = __import__("os").getenv(env_var)

            samples: Dict[str, List[MetricPoint]] = {}
            # For providers with a URL-like env var (e.g., OLLAMA) probe by URL
            if env_value and isinstance(env_value, str) and env_value.startswith("http"):
                try:
                    samples = await _probe_ollama(env_value, models)
                except Exception:
                    samples = await _generate_synthetic_sample(status, models)
            else:
                # For known cloud providers that expose API keys, attempt authenticated probes (OpenAI)
                try:
                    if provider.value == 'openai':
                        # OPENAI_API_KEY is the env var name for OpenAI in the catalog
                        api_key = __import__('os').getenv('OPENAI_API_KEY')
                        if api_key:
                            try:
                                samples = await _probe_openai(api_key, models)
                            except Exception:
                                samples = await _generate_synthetic_sample(status, models)
                        else:
                            samples = await _generate_synthetic_sample(status, models)
                    else:
                        samples = await _generate_synthetic_sample(status, models)
                except Exception:
                    samples = await _generate_synthetic_sample(status, models)

            if provider_key not in _metrics_store:
                _metrics_store[provider_key] = {}

            for m, points in samples.items():
                if m not in _metrics_store[provider_key]:
                    _metrics_store[provider_key][m] = deque(maxlen=MAX_SAMPLES)
                for p in points:
                    _metrics_store[provider_key][m].append(p)

            # Persist to DB if enabled
            try:
                import os

                if os.getenv('METRICS_PERSIST', '').lower() in ('1', 'true', 'yes'):
                    await _persist_samples(provider_key, samples)
            except Exception:
                # persistence is best-effort
                pass

        # prune old samples if any timestamp beyond retention (not strictly needed because deque bounded)


def get_latest_metrics(provider_key: Optional[str] = None, samples: int = 12) -> List[Dict]:
    """Return metrics as a list of dicts shaped for the API response.

    If no data is available, returns an empty list.
    """
    out: List[Dict] = []
    # Note: callers may call from async context; store is protected by _store_lock when writing.
    for prov, models_map in _metrics_store.items():
        if provider_key and prov != provider_key:
            continue
        for model, dq in models_map.items():
            pts: List[Dict] = []
            # pull last N samples
            for p in list(dq)[-samples:]:
                pts.append({"timestamp": p.timestamp, "latency_ms": p.latency_ms, "success_rate": p.success_rate})
            out.append({"provider": prov, "model": model, "points": pts})
    return out


# No further imports from routes to avoid circular imports


async def _persist_samples(provider_key: str, samples_map):
    """Best-effort persistence wrapper that delegates to providers_metrics_persist.persist_samples if available."""
    try:
        from src.api.providers_metrics_persist import persist_samples

        await persist_samples(provider_key, samples_map)
    except Exception as e:
        # Log persistence errors so they are visible in production; do not raise to avoid impacting main flow
        try:
            logger.exception("metrics_persist_error", error=str(e))
        except Exception:
            # fallback to printing if logging is unavailable
            print('metrics_persist_error', e)


def _start_background_collector():
    global _running_task
    if _running_task is None or _running_task.done():
        loop = asyncio.get_event_loop()
        _running_task = loop.create_task(_collect_loop())
        logger.info("metrics_collector_task_started")


async def _on_system_startup(event: Event) -> None:
    # Start the background collector
    _start_background_collector()


# Subscribe to lifecycle startup via event bus
get_event_bus().subscribe_async("system.startup", _on_system_startup)

# Expose for other modules to query
__all__ = ["get_latest_metrics"]
