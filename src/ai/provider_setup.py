"""
Runtime LLM Provider configuration (Y1.0).

Allows the boss to add a model provider + API key from the product UI
(模型与 Provider 页面) instead of editing environment variables.

Responsibilities:
- ``PROVIDER_CATALOG``: provider metadata (type, env vars, defaults, cost)
- :func:`apply_provider_runtime`: register/replace a provider in the live
  Provider Gateway (idempotent, works at runtime)
- :func:`persist_provider_config`: upsert the encrypted config into PostgreSQL
- :func:`load_persisted_providers`: startup loading (env vars are NOT enough
  for UI-added providers)
- :func:`list_persisted_configs` / :func:`delete_persisted_config`: management

Security:
- API keys are encrypted with Fernet (``src.core.encryption``) before storage
- Plaintext keys are never returned by list functions
- All writes go through RBAC ``system:write`` at the API layer
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.encryption import decrypt_value, encrypt_value
from src.database.models import LLMProviderConfigModel

logger = structlog.get_logger(__name__)


# ============================================================================
# Provider catalog (mirrors src/api/app.py PROVIDER_SETUP; kept here so both
# the startup env flow and the runtime UI flow share one source of truth)
# ============================================================================

PROVIDER_CATALOG: Dict[str, Dict[str, Any]] = {
    "openai": {
        "display_name": "OpenAI",
        "type": "openai",
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_CHAT_MODEL",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "context_window": 128000,
        "needs_key": True,
        "supports_functions": True,
        "cost": (0.15, 0.60),
    },
    "anthropic": {
        "display_name": "Anthropic Claude",
        "type": "anthropic",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "model_env": "ANTHROPIC_CHAT_MODEL",
        "default_base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "context_window": 200000,
        "needs_key": True,
        "supports_functions": True,
        "cost": (3.0, 15.0),
    },
    "google": {
        "display_name": "Google Gemini",
        "type": "google",
        "api_key_env": "GOOGLE_API_KEY",
        "base_url_env": "GOOGLE_BASE_URL",
        "model_env": "GOOGLE_CHAT_MODEL",
        "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-1.5-flash",
        "context_window": 1048576,
        "needs_key": True,
        "supports_functions": True,
        "cost": (0.075, 0.30),
    },
    "deepseek": {
        "display_name": "DeepSeek",
        "type": "deepseek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_CHAT_MODEL",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "context_window": 65536,
        "needs_key": True,
        "supports_functions": True,
        "cost": (0.14, 0.28),
    },
    "xai": {
        "display_name": "xAI Grok",
        "type": "xai",
        "api_key_env": "XAI_API_KEY",
        "base_url_env": "XAI_BASE_URL",
        "model_env": "XAI_CHAT_MODEL",
        "default_base_url": "https://api.x.ai/v1",
        "default_model": "grok-2",
        "context_window": 131072,
        "needs_key": True,
        "supports_functions": True,
        "cost": (2.0, 10.0),
    },
    "moonshot": {
        "display_name": "Moonshot Kimi",
        "type": "moonshot",
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url_env": "MOONSHOT_BASE_URL",
        "model_env": "MOONSHOT_CHAT_MODEL",
        "default_base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-8k",
        "context_window": 8192,
        "needs_key": True,
        "supports_functions": True,
        "cost": (0.12, 0.12),
    },
    "ollama": {
        "display_name": "Ollama 本地模型",
        "type": "ollama",
        "api_key_env": None,
        "base_url_env": "OLLAMA_HOST",
        "model_env": "OLLAMA_DEFAULT_MODEL",
        "default_base_url": "http://host.docker.internal:11434",
        "default_model": "qwen2.5:7b",
        "context_window": 32768,
        "needs_key": False,
        "supports_functions": False,
        "cost": (0.0, 0.0),
    },
}


def catalog_for_api() -> List[Dict[str, Any]]:
    """Catalog payload for the frontend add-provider form."""
    return [
        {
            "name": name,
            "display_name": meta["display_name"],
            "default_base_url": meta["default_base_url"],
            "default_model": meta["default_model"],
            "needs_key": meta["needs_key"],
        }
        for name, meta in PROVIDER_CATALOG.items()
    ]


# ============================================================================
# Runtime registration
# ============================================================================

def apply_provider_runtime(
    name: str,
    *,
    api_key: Optional[str],
    base_url: str,
    model: str,
) -> Dict[str, Any]:
    """Register (or replace) a provider in the live Provider Gateway.

    Idempotent: re-adding the same provider replaces its config/instance so
    rotated keys / changed endpoints take effect immediately.

    Raises:
        ValueError: unknown provider name or missing required API key.
    """
    from src.ai.gateway import get_gateway
    from src.ai.providers import ModelConfig, ProviderConfig, ProviderType
    from src.security.secrets import get_secrets_manager

    meta = PROVIDER_CATALOG.get((name or "").lower())
    if not meta:
        raise ValueError(f"未知 Provider: {name}")
    if meta["needs_key"] and not api_key:
        raise ValueError(f"{meta['display_name']} 需要 API Key")

    name = name.lower()
    ptype = ProviderType(meta["type"])
    base_url = (base_url or meta["default_base_url"]).rstrip("/")
    model = model or meta["default_model"]

    # 1) Make credentials resolvable via the env-based secrets manager.
    secrets = get_secrets_manager()
    if meta["needs_key"] and api_key:
        secrets.set_runtime_secret(meta["api_key_env"], api_key)
    if base_url:
        os.environ[meta["base_url_env"]] = base_url
    if model:
        os.environ[meta["model_env"]] = model

    # 2) Replace in the gateway (drop cached instance holding old key/url).
    gateway = get_gateway()
    gateway.unregister_provider(ptype)
    gateway.register_provider(
        ProviderConfig(
            provider=ptype,
            api_key_name=meta["api_key_env"] or "",
            base_url=base_url,
            timeout_seconds=60,
            max_retries=3,
            enabled=True,
            metadata={"model": model, "configured_via": "ui"},
        )
    )

    # 3) Register the provider's own default model. Built-in agents that
    #    target other vendors are served via the gateway's fallback remap
    #    (_maybe_remap_provider), so we deliberately do NOT register other
    #    vendors' model ids under this provider (that would misattribute
    #    e.g. gpt-4 to DeepSeek in the model registry / status UI).
    input_cost, output_cost = meta["cost"]
    try:
        gateway.register_model(
            ModelConfig(
                provider=ptype,
                model_id=model,
                model_name=model,
                context_window=meta["context_window"],
                supports_streaming=True,
                supports_functions=meta["supports_functions"],
                enabled=True,
                input_cost_per_1k=input_cost,
                output_cost_per_1k=output_cost,
            )
        )
    except Exception:
        pass  # already registered

    logger.info(
        "runtime_provider_applied",
        provider=name,
        model=model,
        base_url=base_url,
    )
    return {
        "provider": name,
        "display_name": meta["display_name"],
        "base_url": base_url,
        "model": model,
    }


def unregister_provider_runtime(name: str) -> None:
    """Remove a runtime-added provider from the live gateway."""
    from src.ai.gateway import get_gateway
    from src.ai.providers import ProviderType

    meta = PROVIDER_CATALOG.get((name or "").lower())
    if not meta:
        return
    get_gateway().unregister_provider(ProviderType(meta["type"]))
    logger.info("runtime_provider_removed", provider=name)


async def test_provider_connection(
    name: str,
    *,
    api_key: Optional[str],
    base_url: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Lightweight REAL connectivity probe (metadata endpoint, no business task).

    Returns ``{"status": "healthy"|"error"|"timeout", "detail": str}``.
    Never raises — callers get a structured result for the UI.
    """
    import httpx

    meta = PROVIDER_CATALOG.get((name or "").lower())
    if not meta:
        return {"status": "error", "detail": f"未知 Provider: {name}"}
    name = name.lower()
    base_url = (base_url or meta["default_base_url"]).rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=12) as client:
            if name == "ollama":
                resp = await client.get(f"{base_url}/api/tags")
            elif name == "google":
                resp = await client.get(
                    f"{base_url}/models",
                    params={"key": api_key},
                )
            elif name == "anthropic":
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"x-api-key": api_key or "", "anthropic-version": "2023-06-01"},
                )
            else:
                # OpenAI-compatible: openai / deepseek / moonshot / xai
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key or ''}"},
                )
        if resp.status_code == 200:
            return {"status": "healthy", "detail": "连接成功，凭据有效"}
        if resp.status_code in (401, 403):
            return {"status": "error", "detail": f"认证失败（HTTP {resp.status_code}）：API Key 无效或无权限"}
        return {"status": "error", "detail": f"服务返回 HTTP {resp.status_code}：{resp.text[:150]}"}
    except Exception as e:
        detail = str(e)
        status = "timeout" if "timeout" in detail.lower() else "error"
        return {"status": status, "detail": f"无法连接 {base_url}：{detail[:150]}"}


# ============================================================================
# Persistence (PostgreSQL, encrypted)
# ============================================================================

async def persist_provider_config(
    session: AsyncSession,
    *,
    name: str,
    base_url: Optional[str],
    model: Optional[str],
    api_key: Optional[str],
    created_by: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> LLMProviderConfigModel:
    """Upsert a provider config row. Empty ``api_key`` keeps the stored one."""
    meta = PROVIDER_CATALOG.get((name or "").lower())
    if not meta:
        raise ValueError(f"未知 Provider: {name}")
    name = name.lower()
    base_url = (base_url or meta["default_base_url"]).rstrip("/")
    model = model or meta["default_model"]
    if meta["needs_key"] and not api_key:
        query = select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == name)
        if tenant_id is not None:
            query = query.where(LLMProviderConfigModel.tenant_id == tenant_id)
        existing = await session.scalar(query)
        if not existing or not existing.api_key_encrypted:
            raise ValueError(f"{meta['display_name']} 需要 API Key")

    query = select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == name)
    if tenant_id is not None:
        query = query.where(LLMProviderConfigModel.tenant_id == tenant_id)
    row = await session.scalar(query)
    if row is None:
        row = LLMProviderConfigModel(
            id=str(uuid.uuid4()),
            provider=name,
            created_by=created_by,
            tenant_id=tenant_id,
            owner_id=created_by,
        )
        session.add(row)
    row.display_name = meta["display_name"]
    row.base_url = base_url
    row.model = model
    row.enabled = True
    row.created_by = created_by
    row.tenant_id = tenant_id
    row.owner_id = created_by
    if api_key:
        row.api_key_encrypted = encrypt_value(api_key)
    await session.commit()
    return row


async def list_persisted_configs(
    session: AsyncSession,
    tenant_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List persisted configs with MASKED key info (never the plaintext)."""
    query = select(LLMProviderConfigModel)
    if tenant_id is not None:
        query = query.where(LLMProviderConfigModel.tenant_id == tenant_id)
    query = query.order_by(LLMProviderConfigModel.created_at)
    rows = (await session.scalars(query)).all()
    result: List[Dict[str, Any]] = []
    for row in rows:
        has_key = bool(row.api_key_encrypted)
        key_preview = None
        if has_key:
            try:
                plain = decrypt_value(row.api_key_encrypted) or ""
                key_preview = f"{'*' * max(0, len(plain) - 4)}{plain[-4:]}" if len(plain) >= 4 else "****"
            except Exception:
                key_preview = "****"
        result.append(
            {
                "id": row.id,
                "provider": row.provider,
                "display_name": row.display_name or PROVIDER_CATALOG.get(row.provider, {}).get("display_name", row.provider),
                "base_url": row.base_url,
                "model": row.model,
                "enabled": row.enabled,
                "tenant_id": row.tenant_id,
                "owner_id": row.owner_id,
                "has_api_key": has_key,
                "api_key_preview": key_preview,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
        )
    return result


async def delete_persisted_config(
    session: AsyncSession,
    name: str,
    tenant_id: Optional[str] = None,
) -> bool:
    """Delete a persisted provider config row. Returns True if a row existed."""
    query = select(LLMProviderConfigModel).where(LLMProviderConfigModel.provider == (name or "").lower())
    if tenant_id is not None:
        query = query.where(LLMProviderConfigModel.tenant_id == tenant_id)
    row = await session.scalar(query)
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True


async def load_persisted_providers(session: AsyncSession, tenant_id: Optional[str] = None) -> List[str]:
    """Startup hook: apply all enabled persisted provider configs.

    Called from the FastAPI lifespan after env-based registration so that
    providers/keys added from the UI survive restarts.
    """
    loaded: List[str] = []
    try:
        query = select(LLMProviderConfigModel).where(LLMProviderConfigModel.enabled.is_(True))
        if tenant_id is not None:
            query = query.where(LLMProviderConfigModel.tenant_id == tenant_id)
        rows = (await session.scalars(query)).all()
    except Exception as e:  # table may not exist in fresh test DBs
        logger.warning("persisted_providers_load_skipped", error=str(e))
        return loaded

    for row in rows:
        try:
            api_key = decrypt_value(row.api_key_encrypted) if row.api_key_encrypted else None
            apply_provider_runtime(
                row.provider,
                api_key=api_key,
                base_url=row.base_url,
                model=row.model,
            )
            loaded.append(row.provider)
        except Exception as e:
            logger.error("persisted_provider_apply_failed", provider=row.provider, error=str(e))
    if loaded:
        logger.info("persisted_providers_loaded", providers=loaded)
    return loaded
