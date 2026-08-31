"""
Provider status & configuration endpoints.

- GET  /provider/status      : runtime provider health/status (ModelsPage)
- GET  /provider/catalog     : supported providers for the add-provider form
- GET  /provider/configs     : persisted provider configs (keys masked)
- POST /provider/configs     : add/update a provider + API key (system:write)
- DELETE /provider/configs/{name} : remove a provider config (system:write)
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.provider_setup import (
    PROVIDER_CATALOG,
    apply_provider_runtime,
    catalog_for_api,
    delete_persisted_config,
    list_persisted_configs,
    persist_provider_config,
    test_provider_connection,
    unregister_provider_runtime,
)
from src.api.dependencies import get_current_user
from src.api.dependencies.permissions import require_permission
from src.api.provider_catalog import get_system_provider_status
from src.identity.audit import AuditService
from src.identity.database import get_db_session
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/provider", tags=["provider"])


class ProviderConfigRequest(BaseModel):
    provider: str = Field(..., min_length=1, description="provider 名称，如 deepseek/openai/ollama")
    api_key: str | None = Field(None, description="API Key；更新时留空表示不修改；Ollama 可空")
    base_url: str | None = Field(None, description="API Base URL，留空使用官方默认")
    model: str | None = Field(None, description="默认模型 ID，留空使用 catalog 默认")
    test: bool = Field(False, description="是否立即执行真实连接测试")


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

    # Gateway-registered real providers (covers UI-added DeepSeek/Moonshot/xAI/...)
    try:
        from src.ai.gateway import get_gateway

        checked = {r["type"] for r in results}
        for ptype in get_gateway().list_real_providers():
            if ptype.value in checked:
                continue
            meta = PROVIDER_CATALOG.get(ptype.value, {})
            probe = await test_provider_connection(
                ptype.value,
                api_key=__import__("os").getenv(meta.get("api_key_env") or "", "") or None,
                base_url=__import__("os").getenv(meta.get("base_url_env") or "", meta.get("default_base_url", "")),
            )
            results.append({
                "name": meta.get("display_name", ptype.value),
                "type": ptype.value,
                "status": probe["status"],
                "detail": probe["detail"],
            })
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("provider_gateway_health_check_failed", error=str(e))

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


# ============================================================================
# Runtime provider configuration (产品内添加模型 / API Key)
# ============================================================================

@router.get("/catalog")
async def provider_catalog(
    _: User = Depends(require_permission("system", "read")),
):
    """List supported providers with default base URL / model for the UI form."""
    return {"providers": catalog_for_api()}


@router.get("/configs")
async def list_provider_configs(
    _: User = Depends(require_permission("system", "read")),
    session: AsyncSession = Depends(get_db_session),
):
    """List persisted provider configs. API keys are MASKED (never returned)."""
    configs = await list_persisted_configs(session)
    return {"configs": configs, "total": len(configs)}


@router.post("/configs")
async def upsert_provider_config(
    payload: ProviderConfigRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("system", "write")),
    session: AsyncSession = Depends(get_db_session),
):
    """Add or update a model provider + API key.

    Persists the encrypted key in PostgreSQL, applies the provider to the
    live gateway immediately (no restart needed), and optionally runs a
    real connection test.
    """
    name = (payload.provider or "").lower()
    meta = PROVIDER_CATALOG.get(name)
    if not meta:
        raise HTTPException(status_code=400, detail=f"不支持的 Provider: {payload.provider}")

    base_url = (payload.base_url or meta["default_base_url"]).rstrip("/")
    model = payload.model or meta["default_model"]

    # Optional real connectivity test BEFORE persisting (fail-closed)
    health = None
    if payload.test:
        key_for_test = payload.api_key
        if not key_for_test and meta["needs_key"]:
            from src.core.encryption import decrypt_value
            existing = await list_persisted_configs(session)
            for cfg in existing:
                if cfg["provider"] == name and cfg["has_api_key"]:
                    # Re-probe stored key: fetch row and decrypt
                    from sqlalchemy import select as _select
                    from src.database.models import LLMProviderConfigModel

                    row = await session.scalar(
                        _select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == name)
                    )
                    key_for_test = decrypt_value(row.api_key_encrypted) if row else None
                    break
        health = await test_provider_connection(name, api_key=key_for_test, base_url=base_url, model=model)
        if health["status"] != "healthy":
            await AuditService.log_failure(
                session=session,
                action="provider_config_test_failed",
                resource_type="provider",
                error_message=health["detail"],
                user_id=getattr(current_user, "id", None),
                resource_id=name,
                details={"detail": health["detail"]},
            )
            raise HTTPException(
                status_code=400,
                detail=f"连接测试失败：{health['detail']}",
            )

    # Persist (encrypted) then apply to the live gateway
    try:
        row = await persist_provider_config(
            session,
            name=name,
            base_url=base_url,
            model=model,
            api_key=payload.api_key,
            created_by=getattr(current_user, "id", None),
        )
        from src.core.encryption import decrypt_value

        apply_provider_runtime(
            name,
            api_key=decrypt_value(row.api_key_encrypted) if row.api_key_encrypted else None,
            base_url=row.base_url,
            model=row.model,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Refresh exported status so /provider/status reflects the new provider
    try:
        from src.api.app import refresh_provider_status

        refresh_provider_status()
    except Exception:  # pragma: no cover - defensive
        pass

    await AuditService.log_success(
        session=session,
        action="provider_configured",
        resource_type="provider",
        user_id=getattr(current_user, "id", None),
        resource_id=name,
        details={"model": model, "base_url": base_url, "tested": bool(payload.test)},
    )

    configs = await list_persisted_configs(session)
    saved = next((c for c in configs if c["provider"] == name), None)
    return {"status": "configured", "config": saved, "health": health}


@router.delete("/configs/{name}")
async def remove_provider_config(
    name: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("system", "write")),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a persisted provider config and unregister it at runtime."""
    name = (name or "").lower()
    existed = await delete_persisted_config(session, name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"未找到 Provider 配置: {name}")

    unregister_provider_runtime(name)
    try:
        from src.api.app import refresh_provider_status

        refresh_provider_status()
    except Exception:  # pragma: no cover - defensive
        pass

    await AuditService.log_success(
        session=session,
        action="provider_removed",
        resource_type="provider",
        user_id=getattr(current_user, "id", None),
        resource_id=name,
        details={},
    )
    return {"status": "removed", "provider": name}