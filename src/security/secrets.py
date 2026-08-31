"""
Layer 1: Security & Governance
Secrets Management - API Keys NEVER in code/Git/logs
"""

import os
from typing import Dict, Optional

import structlog

from src.core.config import get_settings
from src.core.errors import ConfigurationError

logger = structlog.get_logger(__name__)


class SecretManager:
    """A lightweight secret manager compatible with the requested Phase 5 secret contract."""

    def __init__(self):
        self._secrets: Dict[str, str] = {}

    def store_secret(self, key: str, value: str) -> str:
        self._secrets[key] = value
        return value

    def get_secret(self, key: str) -> Optional[str]:
        return self._secrets.get(key)

    def rotate_secret(self, key: str, new_value: str) -> str:
        self._secrets[key] = new_value
        return new_value

    def delete_secret(self, key: str) -> None:
        self._secrets.pop(key, None)


class SecretsManager:
    """
    Secure secrets management

    CRITICAL SECURITY RULES:
    1. Secrets ONLY from environment variables
    2. NEVER log secret values
    3. NEVER commit secrets to Git
    4. NEVER return raw secrets in API responses
    """

    def __init__(self):
        self.settings = get_settings()
        self._secrets_cache: Dict[str, str] = {}
        logger.info("secrets_manager_initialized")

    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Get a secret from environment variables

        Args:
            key: Secret key name
            required: If True, raise error if secret not found

        Returns:
            Secret value (NEVER log this)

        Raises:
            ConfigurationError: If required secret is missing
        """
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # Get from environment
        value = os.getenv(key)
        if value is None:
            if required:
                logger.error("secret_missing", key=key)
                raise ConfigurationError(f"Required secret not found: {key}")
            logger.warning("secret_optional_missing", key=key)
            return None

        # Cache the secret (in memory only, never persisted)
        self._secrets_cache[key] = value

        # CRITICAL: Never log the actual value
        logger.info("secret_loaded", key=key, value_length=len(value))

        return value

    def get(self, key: str, required: bool = True) -> Optional[str]:
        """Alias for :meth:`get_secret` — provider implementations
        (OpenAI/Anthropic/DeepSeek/...) call ``secrets_manager.get(...)``."""
        return self.get_secret(key, required=required)

    def set_runtime_secret(self, key: str, value: str) -> None:
        """Inject a secret provided at runtime (e.g. API Key added via the
        product UI). Persisted encrypted in the DB; mirrored into the process
        environment so the env-based resolution path serves it. NEVER logged.
        """
        if not key or not value:
            return
        os.environ[key] = value
        self._secrets_cache[key] = value
        logger.info("runtime_secret_stored", key=key, value_length=len(value))

    def get_database_password(self) -> str:
        """Get database password"""
        return self.settings.postgres_password

    def get_redis_password(self) -> Optional[str]:
        """Get Redis password (optional)"""
        return self.settings.redis_password or None

    def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        return self.settings.jwt_secret_key

    def get_app_secret(self) -> str:
        """Get application secret key"""
        return self.settings.secret_key

    def validate_secrets(self) -> bool:
        """
        Validate that all required secrets are present

        Returns:
            True if all required secrets are valid

        Raises:
            ConfigurationError: If any required secret is invalid
        """
        logger.info("validating_secrets")

        errors = []

        # Check database password
        if not self.settings.postgres_password:
            errors.append("POSTGRES_PASSWORD")

        # Check secret key
        if not self.settings.secret_key or len(self.settings.secret_key) < 32:
            errors.append("SECRET_KEY (must be at least 32 characters)")

        # Check JWT secret
        if not self.settings.jwt_secret_key or len(self.settings.jwt_secret_key) < 32:
            errors.append("JWT_SECRET_KEY (must be at least 32 characters)")

        if errors:
            error_msg = f"Missing or invalid secrets: {', '.join(errors)}"
            logger.error("secrets_validation_failed", errors=errors)
            raise ConfigurationError(error_msg)

        logger.info("secrets_validation_passed")
        return True

    def clear_cache(self) -> None:
        """Clear secrets cache (for testing or security rotation)"""
        logger.info("secrets_cache_cleared")
        self._secrets_cache.clear()



# 同源的默认值名单（与 core/config.py reject_default_secrets 保持一致，并扩展 docker-compose 占位值）
_KNOWN_DEFAULT_SECRETS = {
    # core/config.py 默认
    "01234567890123456789012345678901",
    "abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
    # docker-compose.yml 占位值
    "change-me-please-use-a-long-random-value",
}

_KNOWN_WEAK_POSTGRES_PASSWORDS = {
    "liuhao_pass",
    "change-me",
    "postgres",
    "password",
    "root",
    "admin",
    "123456",
    "",
}


def check_production_secrets(settings) -> Dict[str, object]:
    """纯函数：生产密钥自检。

    生产环境使用默认/占位密钥 → ok=False；开发环境仅写入 warnings。
    """
    env = getattr(settings, "app_env", "development")
    is_prod = (str(env).lower() == "production")

    failed_checks: list[str] = []
    warnings: list[str] = []

    secret_key = str(getattr(settings, "secret_key", "") or "")
    jwt_secret_key = str(getattr(settings, "jwt_secret_key", "") or "")
    postgres_password = str(getattr(settings, "postgres_password", "") or "")

    if len(secret_key) < 32:
        msg = "secret_key: length < 32 (必须 >= 32 字符)"
        (failed_checks if is_prod else warnings).append(msg)
    if len(jwt_secret_key) < 32:
        msg = "jwt_secret_key: length < 32 (必须 >= 32 字符)"
        (failed_checks if is_prod else warnings).append(msg)

    if secret_key in _KNOWN_DEFAULT_SECRETS:
        msg = (
            "secret_key: 使用了已知默认或 docker-compose 占位值，"
            "请通过环境变量 SECRET_KEY 设置至少 32 位随机字符串"
        )
        (failed_checks if is_prod else warnings).append(msg)
    if jwt_secret_key in _KNOWN_DEFAULT_SECRETS:
        msg = (
            "jwt_secret_key: 使用了已知默认或 docker-compose 占位值，"
            "请通过环境变量 JWT_SECRET_KEY 设置至少 32 位随机字符串"
        )
        (failed_checks if is_prod else warnings).append(msg)

    if postgres_password in _KNOWN_WEAK_POSTGRES_PASSWORDS:
        warnings.append(
            "postgres_password: 使用了弱密码/占位值，生产环境请通过环境变量 POSTGRES_PASSWORD 设置强密码"
        )

    ok = (not is_prod) or (not failed_checks)
    return {
        "ok": bool(ok),
        "env": str(env),
        "failed_checks": failed_checks,
        "warnings": warnings,
    }
# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager (Singleton)"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret_manager() -> SecretManager:
    """Compatibility alias to the requested Phase 5 lightweight SecretManager."""
    return SecretManager()


def reset_secrets_manager() -> None:
    """Reset secrets manager (for testing only)"""
    global _secrets_manager
    if _secrets_manager is not None:
        _secrets_manager.clear_cache()
    _secrets_manager = None

