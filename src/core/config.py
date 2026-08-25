"""
Layer 0: Core Runtime
Configuration management with security-first design
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with security-first defaults
    All secrets must be loaded from environment variables
    """

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Application
    app_env: str = Field(
        default="development", description="Environment: development/staging/production"
    )
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_debug: bool = Field(default=False)

    # Database - support both direct URL and PostgreSQL components
    database_url: Optional[str] = Field(
        default=None, description="Direct database URL (SQLite/PostgreSQL)"
    )
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="liuhao_ai_os")
    postgres_user: str = Field(default="liuhao_user")
    postgres_password: str = Field(
        default="", description="MUST be set via environment variable for PostgreSQL"
    )

    # Database Connection Pool (Phase 2)
    database_pool_size: int = Field(default=5, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Max connections beyond pool_size")
    database_echo: bool = Field(default=False, description="Echo SQL statements (debug)")

    # Backup Configuration (Phase 2)
    backup_enabled: bool = Field(default=True, description="Enable automated backups")
    backup_dir: str = Field(default="./backups", description="Backup directory")
    backup_schedule_hours: int = Field(default=1, description="Backup interval in hours")

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)

    # Security
    secret_key: str = Field(default="", description="MUST be set via environment variable")
    jwt_secret_key: str = Field(default="", description="MUST be set via environment variable")
    jwt_algorithm: str = Field(default="HS256")

    # Ollama (Week 4: Local LLM)
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API endpoint")
    ollama_default_model: str = Field(default="qwen2.5:7b", description="Default Ollama model")
    ollama_timeout: int = Field(default=60, description="Ollama request timeout in seconds")
    ollama_enabled: bool = Field(default=False, description="Enable Ollama provider")
    jwt_expiration_hours: int = Field(default=24)

    # Policy Defaults (Fail Closed)
    policy_default_deny: bool = Field(default=True, description="Default DENY for unknown policies")
    policy_unknown_deny: bool = Field(default=True, description="DENY for unknown resources")

    # Feature Flags (Security First - all disabled by default)
    feature_provider_gateway: bool = Field(default=False)
    feature_network_gateway: bool = Field(default=False)
    feature_browser_gateway: bool = Field(default=False)
    feature_external_tools: bool = Field(default=False)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/app.log")

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def validate_secrets(cls, v: str, info) -> str:
        """Validate that critical secrets are set"""
        if not v or len(v) < 32:
            raise ValueError(
                f"{info.field_name} must be set via environment variable and be at least 32 characters"
            )
        return v

    def get_database_url(self) -> str:
        """
        Get database URL - prefer explicit DATABASE_URL, fallback to PostgreSQL components
        """
        if self.database_url:
            return self.database_url
        # Fallback to PostgreSQL
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.app_env == "development"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance (Singleton pattern)
    This is the ONLY way to access configuration in the application
    """
    global _settings
    if _settings is None:
        project_root = Path(__file__).resolve().parents[1]
        env_candidates = [
            project_root / ".env",
            project_root / ".env.local",
            project_root / ".env.development",
            project_root / ".env.production",
        ]
        for env_file in env_candidates:
            if env_file.exists():
                load_dotenv(env_file, override=False)

        if os.environ.get("APP_ENV") == "production":
            prod_env = project_root / ".env.production"
            if prod_env.exists():
                load_dotenv(prod_env, override=False)

        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings (for testing only)"""
    global _settings
    _settings = None
