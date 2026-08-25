"""
Layer 0: Core Runtime
Logging configuration with security-aware filtering
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.core.config import get_settings


def mask_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Mask sensitive data in logs (API keys, passwords, tokens)
    CRITICAL: Prevent secrets from appearing in logs
    """
    sensitive_keys = {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "api-key",
        "authorization",
        "auth",
        "jwt",
        "secret_key",
        "postgres_password",
        "redis_password",
    }

    def _mask_value(key: str, value: Any) -> Any:
        """Recursively mask sensitive values"""
        if isinstance(value, dict):
            return {k: _mask_value(k, v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [_mask_value(key, item) for item in value]
        elif any(sensitive in key.lower() for sensitive in sensitive_keys):
            return "***REDACTED***"
        return value

    return {k: _mask_value(k, v) for k, v in event_dict.items()}


def configure_logging() -> None:
    """
    Configure structured logging with security filtering
    All logs are structured JSON by default for better observability
    """
    settings = get_settings()

    # Ensure log directory exists
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        mask_sensitive_data,  # CRITICAL: Always mask sensitive data
    ]

    # Add format-specific processor
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # File handler
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance"""
    return structlog.get_logger(name)
