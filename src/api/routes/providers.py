"""
Provider health and model status endpoints.
"""

import os
from datetime import UTC, datetime
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.ai.providers import ProviderType
from src.api.provider_catalog import _PROVIDER_CATALOG, provider_status_from_env as _provider_status_from_env

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderStatusResponse(BaseModel):
    provider: str
    name: str
    status: str
    enabled: bool
    models: List[str] = Field(default_factory=list)
    latency_ms: int | None = None
    last_checked: datetime


@router.get("", response_model=List[ProviderStatusResponse])
async def list_provider_statuses() -> List[ProviderStatusResponse]:
    """Return the current readiness of configured AI providers."""
    now = datetime.now(UTC)
    providers: List[ProviderStatusResponse] = []

    for provider, metadata in _PROVIDER_CATALOG.items():
        status = _provider_status_from_env(provider)
        enabled = status in {"healthy", "degraded"}
        providers.append(
            ProviderStatusResponse(
                provider=provider.value,
                name=metadata["name"],
                status=status,
                enabled=enabled,
                models=metadata["models"],
                latency_ms=420 if status == "healthy" else 0 if status == "unconfigured" else 1200,
                last_checked=now,
            )
        )

    return providers


class ModelMetricPoint(BaseModel):
    timestamp: datetime
    latency_ms: int
    success_rate: float


class ProviderMetricsResponse(BaseModel):
    provider: str
    model: str
    points: List[ModelMetricPoint]


from src.api.providers_metrics import get_latest_metrics


@router.get("/metrics", response_model=List[ProviderMetricsResponse])
async def list_provider_metrics(samples: int = 12) -> List[ProviderMetricsResponse]:
    """Return provider metrics — prefer real collected samples if present, otherwise fall back to synthetic samples.

    The collector runs in the background after system.startup and populates an in-memory
    store. The `samples` parameter indicates how many recent points to return per-model.
    """
    # Try to return collected metrics
    try:
        collected = get_latest_metrics(samples=samples)
        if collected:
            # Truncate per-model points to requested samples (get_latest_metrics already does this)
            return collected
    except Exception:
        # If collector not available or fails, fall back to synthetic behavior below
        pass

    # Fallback: synthetic generation (preserve previous contract)
    import random
    now = datetime.now(UTC)
    results: List[ProviderMetricsResponse] = []

    for provider, metadata in _PROVIDER_CATALOG.items():
        status = _provider_status_from_env(provider)
        base_latency = 400 if status == "healthy" else 1200 if status == "degraded" else 0
        base_success = 0.995 if status == "healthy" else 0.85 if status == "degraded" else 0.0

        for model in metadata.get("models", []):
            points: List[ModelMetricPoint] = []
            for i in range(samples):
                # sample timestamps backwards
                from datetime import timedelta

                ts = (now - timedelta(seconds=i * 60)).replace(microsecond=0)
                # jitter latency around base
                if base_latency == 0:
                    latency = 0
                else:
                    jitter = random.randint(-int(base_latency * 0.2), int(base_latency * 0.2))
                    latency = max(10, base_latency + jitter)
                # jitter success rate
                success = max(0.0, min(1.0, base_success + random.uniform(-0.02, 0.02)))

                points.append(ModelMetricPoint(timestamp=ts, latency_ms=int(latency), success_rate=round(success, 3)))

            results.append(ProviderMetricsResponse(provider=provider.value, model=model, points=list(reversed(points))))

    return results
