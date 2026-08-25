"""
Layer 0: Core Runtime
"""

from src.core.config import Settings, get_settings
from src.core.errors import (
    AlreadyExistsError,
    AuthenticationError,
    ConfigurationError,
    DatabaseError,
    ErrorCode,
    ExternalServiceError,
    LiuHaoError,
    NotFoundError,
    PermissionDeniedError,
    PolicyViolationError,
    SecurityError,
    ValidationError,
)
from src.core.events import Event, EventBus, get_event_bus
from src.core.lifecycle import get_lifecycle_manager, lifespan_context
from src.core.logging import configure_logging, get_logger

__all__ = [
    # Config
    "get_settings",
    "Settings",
    # Events
    "get_event_bus",
    "Event",
    "EventBus",
    # Errors
    "LiuHaoError",
    "ErrorCode",
    "ConfigurationError",
    "SecurityError",
    "AuthenticationError",
    "PermissionDeniedError",
    "PolicyViolationError",
    "ValidationError",
    "NotFoundError",
    "AlreadyExistsError",
    "DatabaseError",
    "ExternalServiceError",
    # Logging
    "configure_logging",
    "get_logger",
    # Lifecycle
    "get_lifecycle_manager",
    "lifespan_context",
]
