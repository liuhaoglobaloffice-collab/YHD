"""
Layer 0: Core Runtime
Unified error handling with security context
"""

from enum import Enum
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes"""

    # Generic
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    EXECUTION_ERROR = "EXECUTION_ERROR"

    # Configuration
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    MISSING_SECRET = "MISSING_SECRET"

    # Security
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    POLICY_VIOLATION = "POLICY_VIOLATION"

    # Policy Engine
    POLICY_EVALUATION_FAILED = "POLICY_EVALUATION_FAILED"
    UNKNOWN_POLICY = "UNKNOWN_POLICY"
    DEFAULT_DENY = "DEFAULT_DENY"

    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"

    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Database
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"

    # External
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    GATEWAY_ERROR = "GATEWAY_ERROR"


class LiuHaoError(Exception):
    """
    Base exception for all LiuHao AI OS errors
    Includes security context and structured logging
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.user_id = user_id
        self.resource = resource

        # Log error with context
        logger.error(
            "liuhao_error",
            message=message,
            code=code,
            details=self.details,
            user_id=user_id,
            resource=resource,
        )


class ConfigurationError(LiuHaoError):
    """Configuration related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.CONFIGURATION_ERROR, **kwargs)


class SecurityError(LiuHaoError):
    """Security related errors"""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.FORBIDDEN, **kwargs):
        super().__init__(message, code=code, **kwargs)


class AuthenticationError(SecurityError):
    """Authentication failures"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, code=ErrorCode.AUTHENTICATION_FAILED, **kwargs)


class PermissionDeniedError(SecurityError):
    """Permission denied (Fail Closed)"""

    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, code=ErrorCode.PERMISSION_DENIED, **kwargs)


class PolicyViolationError(SecurityError):
    """Policy evaluation failure or violation"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.POLICY_VIOLATION, **kwargs)


class ValidationError(LiuHaoError):
    """Input validation errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.VALIDATION_ERROR, **kwargs)


class NotFoundError(LiuHaoError):
    """Resource not found"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.NOT_FOUND, **kwargs)


class AlreadyExistsError(LiuHaoError):
    """Resource already exists"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.ALREADY_EXISTS, **kwargs)


class DatabaseError(LiuHaoError):
    """Database related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.DATABASE_ERROR, **kwargs)


class ExternalServiceError(LiuHaoError):
    """External service errors (Provider, Network, Browser)"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.EXTERNAL_SERVICE_ERROR, **kwargs)


class AIProviderError(ExternalServiceError):
    """AI Provider specific errors (OpenAI, Claude, Ollama, etc.)"""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        if provider:
            message = f"[{provider}] {message}"
        super().__init__(message, **kwargs)


class ResourceNotFoundError(NotFoundError):
    """Alias for NotFoundError (for compatibility)"""

    pass


class ExecutionError(LiuHaoError):
    """Workflow/Task execution errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code=ErrorCode.EXECUTION_ERROR, **kwargs)
