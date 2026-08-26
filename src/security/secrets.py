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
