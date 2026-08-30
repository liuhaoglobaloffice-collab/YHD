"""
Shared provider catalog and environment-based status helper.
This module centralizes the small provider catalog so other modules (routes, metrics collector)
can import it without circular dependencies.
"""
from __future__ import annotations

import os
from typing import Dict

from src.ai.providers import ProviderType

_PROVIDER_CATALOG: Dict[ProviderType, Dict] = {
    ProviderType.OPENAI: {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.1"],
        "env_var": "OPENAI_API_KEY",
    },
    ProviderType.ANTHROPIC: {
        "name": "Anthropic",
        "models": ["claude-3-5-sonnet", "claude-3-haiku"],
        "env_var": "ANTHROPIC_API_KEY",
    },
    ProviderType.GOOGLE: {
        "name": "Google Gemini",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
        "env_var": "GOOGLE_API_KEY",
    },
    ProviderType.XAI: {
        "name": "xAI",
        "models": ["grok-2", "grok-beta"],
        "env_var": "XAI_API_KEY",
    },
    ProviderType.DEEPSEEK: {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "env_var": "DEEPSEEK_API_KEY",
    },
    ProviderType.MOONSHOT: {
        "name": "Moonshot Kimi",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k"],
        "env_var": "MOONSHOT_API_KEY",
    },
    ProviderType.OLLAMA: {
        "name": "Ollama Local",
        "models": ["qwen2.5:7b", "llama3.1:8b"],
        "env_var": "OLLAMA_HOST",
    },
}


def provider_status_from_env(provider: ProviderType) -> str:
    """Infer a simple status string from environment vars for a provider."""
    metadata = _PROVIDER_CATALOG.get(provider, {})
    env_var = metadata.get("env_var")
    if not env_var:
        return "disabled"
    value = os.getenv(env_var)
    if not value:
        return "unconfigured"
    if provider == ProviderType.OLLAMA:
        return "healthy" if str(value).startswith(("http://", "https://")) else "degraded"
    return "healthy"


def get_system_provider_status() -> dict:
    """Get the overall system provider status.
    
    Returns a dict with:
    - configured: bool (whether any real provider is configured)
    - providers: list of provider statuses
    - using_mock: bool (whether mock fallback is active)
    - production_blocked: bool (production mode with no real provider)
    """
    from src.api.app import _provider_status as status
    if status is None:
        status = {"configured": False, "provider": "none", "registered_any": False,
                  "using_mock": True, "production_blocked": False,
                  "environment": "development"}
    
    providers = []
    for ptype, metadata in _PROVIDER_CATALOG.items():
        pstatus = provider_status_from_env(ptype)
        providers.append({
            "name": metadata["name"],
            "type": ptype.value,
            "status": pstatus,
            "env_var": metadata["env_var"],
            "models": metadata["models"],
        })
    
    return {
        **status,
        "providers": providers,
    }
