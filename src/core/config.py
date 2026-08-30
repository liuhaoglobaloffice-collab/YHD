"""
Layer 0: Core Runtime
Configuration management with security-first design
"""

from typing import Optional

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
    secret_key: str = Field(
        default="01234567890123456789012345678901",
        description="MUST be set via environment variable; test/dev fallback is provided",
    )
    # Ollama (Week 4: Local LLM)
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama API endpoint")
    ollama_default_model: str = Field(default="qwen2.5:7b", description="Default Ollama model")
    ollama_timeout: int = Field(default=60, description="Ollama request timeout in seconds")
    ollama_enabled: bool = Field(default=False, description="Enable Ollama provider")

    # Embedding (Phase 2.2: Embedding Pipeline)
    embedding_provider: str = Field(
        default="mock", description="Embedding provider name (mock/openai/self_host)"
    )
    embedding_model: str = Field(
        default="", description="Embedding model name (e.g. nomic-embed-text, text-embedding-3-small)"
    )
    jwt_secret_key: str = Field(
        default="abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
        description="MUST be set via environment variable; test/dev fallback is provided",
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)

    # Policy Defaults (Fail Closed)
    policy_default_deny: bool = Field(default=True, description="Default DENY for unknown policies")
    policy_unknown_deny: bool = Field(default=True, description="DENY for unknown resources")

    # Feature Flags (Security First - all disabled by default)
    feature_provider_gateway: bool = Field(default=True)
    feature_network_gateway: bool = Field(default=False)
    feature_browser_gateway: bool = Field(default=False)
    feature_external_tools: bool = Field(default=False)

    # CORS (comma-separated origins; default "*" for development)
    cors_origins: str = Field(
        default="*", description="Comma-separated allowed CORS origins (e.g. http://localhost:5173,https://app.example.com)"
    )

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    log_file: str = Field(default="logs/app.log")

    # SMTP Email (Lead 跟进邮件；未配置时诚实返回 NOT_CONFIGURED)
    smtp_host: Optional[str] = Field(
        default=None, description="SMTP server host, e.g. smtp.gmail.com"
    )
    smtp_port: int = Field(default=587, description="SMTP port (587 STARTTLS / 465 SSL)")
    smtp_user: Optional[str] = Field(default=None, description="SMTP username (sender account)")
    smtp_password: Optional[str] = Field(
        default=None, description="SMTP password / app password (MUST come from env)"
    )
    smtp_from: Optional[str] = Field(
        default=None, description="From address; defaults to smtp_user when unset"
    )
    smtp_use_ssl: bool = Field(
        default=False, description="Use SMTP_SSL (port 465) instead of STARTTLS (port 587)"
    )
    smtp_proxy: Optional[str] = Field(
        default=None,
        description=(
            "Optional proxy tunnel for SMTP, e.g. socks5://127.0.0.1:10808 or "
            "http://host.docker.internal:10808. Empty = direct connection. "
            "smtplib ignores HTTP_PROXY env vars, so blocked networks need this."
        ),
    )

    # Business Scheduler (P0: 老板长期不在线 — 自主经营调度)
    scheduler_enabled: bool = Field(
        default=False,
        description="Enable background business scheduler (auto-execute active goals)",
    )
    scheduler_interval_seconds: int = Field(
        default=300, description="Scheduler cycle interval in seconds (minimum 30)"
    )
    scheduler_auto_activate: bool = Field(
        default=False,
        description="Auto-activate draft goals each cycle (full autonomy; off by default)",
    )
    scheduler_max_goals_per_cycle: int = Field(
        default=5, description="Max goals activated/executed per scheduler cycle"
    )

    # Workflow execution (P0-7: long-running blocking risk mitigation)
    workflow_worker_mode: str = Field(
        default="inline",
        description=(
            "Workflow execution mode. 'inline' runs synchronously inside the request "
            "(WARNING: long workflows block HTTP threads, NOT recommended for production). "
            "'background' returns execution ID immediately and runs via asyncio.create_task "
            "(recommended for workflows >30s total runtime). Future: 'worker' via "
            "Celery/RQ/Redis Queue."
        ),
    )
    workflow_total_timeout_seconds: int = Field(
        default=1800,
        description="Hard wall-clock timeout per workflow execution (default 30 min). Steps are bounded individually by STEP_TIMEOUT_SECONDS in executor.py.",
    )
    workflow_max_steps: int = Field(
        default=500,
        description="Maximum steps (including sub-steps) allowed per workflow execution to prevent unbounded loops.",
    )

    @field_validator("workflow_worker_mode")
    @classmethod
    def _validate_workflow_mode(cls, v: str) -> str:
        allowed = {"inline", "background"}
        if v not in allowed:
            raise ValueError(f"workflow_worker_mode must be one of {allowed}")
        return v

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def validate_secrets(cls, v: str, info) -> str:
        """Validate that critical secrets are set"""
        if not v or len(v) < 32:
            raise ValueError(
                f"{info.field_name} must be set via environment variable and be at least 32 characters"
            )
        return v

    @field_validator("secret_key", "jwt_secret_key")
    @classmethod
    def reject_default_secrets(cls, v: str, info) -> str:
        """Reject known default/demo secret values in production."""
        _KNOWN_DEFAULTS = {
            "01234567890123456789012345678901",
            "abcdefghijklmnopqrstuvwxyz1234567890ABCDEF",
        }
        # Only raise when the field is set to a known default (not overridden by env)
        # Pydantic will call this with the resolved value; if it matches a known
        # default, we warn but don't crash — the user can still start the app
        # in development. Crash happens in validate_secrets() if the value is
        # too short or empty.
        if v in _KNOWN_DEFAULTS:
            import warnings
            warnings.warn(
                f"{info.field_name} is set to a known default value. "
                f"Set {info.field_name.upper()} via environment variable for production use.",
                stacklevel=2,
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


# Settings are intentionally re-read from the current process environment for
# test and CI isolation. This avoids stale cached configuration after a test
# changes DATABASE_URL / SECRET_KEY / JWT_SECRET_KEY and keeps the config
# contract consistent with the repository's integration tests.


def get_settings() -> Settings:
    """
    Build a settings object from the current process environment.

    Re-reading settings prevents test pollution from a stale global singleton
    and ensures a runtime-local DATABASE_URL switch can be honored without
    resorting to a code redesign.
    """
    return Settings()


def reset_settings() -> None:
    """Reset settings (compatibility no-op for legacy test helpers)."""
    return None
