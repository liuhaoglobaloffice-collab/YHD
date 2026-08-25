"""
Persistence helper for provider metrics. Writes samples into ProviderMetricSample table.
This module is optional and only used when METRICS_PERSIST is enabled.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List
import asyncio

from sqlalchemy import insert
import structlog

from src.database.base import get_session_factory
from src.database.provider_metrics_model import ProviderMetricSample

logger = structlog.get_logger(__name__)


async def persist_samples(provider: str, samples: Dict[str, List]):
    """Persist samples dict: model -> list[MetricPoint] where MetricPoint has timestamp, latency_ms, success_rate

    Implements a best-effort retry (1 retry) and logs errors instead of raising to avoid impacting metrics collection.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        # Build insert statements
        to_insert = []
        for model, pts in samples.items():
            for p in pts:
                ts = p.timestamp if hasattr(p, 'timestamp') else p.get('timestamp')
                latency = p.latency_ms if hasattr(p, 'latency_ms') else p.get('latency_ms')
                success = p.success_rate if hasattr(p, 'success_rate') else p.get('success_rate')
                to_insert.append({
                    'provider': provider,
                    'model': model,
                    'timestamp': ts,
                    'latency_ms': latency,
                    'success_rate': success,
                })
        if not to_insert:
            return

        # Try once, with a single retry on failure
        try:
            await session.execute(insert(ProviderMetricSample), to_insert)
            await session.commit()
            return
        except Exception as e:
            logger.exception("persist_samples_first_attempt_failed", error=str(e))
            # small backoff then retry
            try:
                await asyncio.sleep(0.2)
                await session.execute(insert(ProviderMetricSample), to_insert)
                await session.commit()
                return
            except Exception as e2:
                logger.exception("persist_samples_retry_failed", error=str(e2))
                # do not raise; metrics persistence must not break main flow
                return
