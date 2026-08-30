"""
Provider status endpoint - Shows current LLM provider configuration status.
Used by the ModelsPage frontend to display real provider state.

P2-6: supports an optional ``check=true`` query parameter that performs real
connection health checks (lightweight metadata calls, no business tasks).
"""

import structlog
from fastapi import APIRouter

from src.api.provider_catalog import get_system_provider_status

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/provider", tags=["provider"])


async def run_provider_health_checks() -> list:
    """Run real connection health checks for the LLM providers.

    Only checks providers backed by real implementations in the unified
    provider registry (self_host/Ollama and openai). Checks use lightweight
    metadata endpoints (list models), never execute business tasks.

    Returns a list of ``{name, type, status, detail}`` dicts where status is
    one of: healthy / unavailable / timeout / error.
    """
    results = []

    # Ollama (self_host) - real connection check
    try:
        from src.providers.self_host import SelfHostProvider

        ollama_result = await SelfHostProvider().health_check()
        results.append({
            "name": "Ollama Local",
            "type": "ollama",
            "status": ollama_result["status"],
            "detail": ollama_result["detail"],
        })
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("provider_health_check_failed", provider="ollama", error=str(e))
        results.append({
            "name": "Ollama Local",
            "type": "ollama",
            "status": "error",
            "detail": str(e),
        })

    # OpenAI - real connection check (unavailable when key is missing)
    try:
        from src.providers.openai import OpenAIProvider

        openai_result = await OpenAIProvider().health_check()
        results.append({
            "name": "OpenAI",
            "type": "openai",
            "status": openai_result["status"],
            "detail": openai_result["detail"],
        })
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("provider_health_check_failed", provider="openai", error=str(e))
        results.append({
            "name": "OpenAI",
            "type": "openai",
            "status": "error",
            "detail": str(e),
        })

    return results


@router.get("/status")
async def provider_status(check: bool = False):
    """
    Get the current LLM provider status.

    Args:
        check: When True, perform real connection health checks
               (lightweight metadata calls, no business tasks).

    Returns:
        - configured: bool (whether any real provider is configured)
        - providers: list of provider details with status
        - using_mock: bool (whether mock fallback is active)
        - production_blocked: bool (production mode with no real provider)
        - environment: current environment
        - health_checks: (only when check=True) real connection check results
    """
    status = get_system_provider_status()
    if check:
        status["health_checks"] = await run_provider_health_checks()
    return status