"""
Authentication service with JWT tokens
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import bcrypt
import structlog
from jose import JWTError, jwt

from src.core.config import get_settings
from src.core.errors import AuthenticationError
from src.security.secrets import get_secrets_manager

logger = structlog.get_logger(__name__)


def hash_password(password: str) -> str:
    """Hash a password"""
    # 直接使用 bcrypt 库，避免 passlib 兼容性问题
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # 直接使用 bcrypt 库，避免 passlib 兼容性问题
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token

    Args:
        data: Token payload
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    secrets = get_secrets_manager()

    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=settings.jwt_expiration_hours)

    to_encode.update({"exp": expire})

    # CRITICAL: Use secret from secrets manager, never hardcoded
    encoded_jwt = jwt.encode(
        to_encode,
        secrets.get_jwt_secret(),
        algorithm=settings.jwt_algorithm,
    )

    logger.info("access_token_created", expires_at=expire.isoformat())

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        AuthenticationError: If token is invalid or expired
    """
    settings = get_settings()
    secrets = get_secrets_manager()

    try:
        payload = jwt.decode(
            token,
            secrets.get_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
        )
        return payload

    except JWTError as e:
        logger.warning("token_decode_failed", error=str(e))
        raise AuthenticationError("Invalid or expired token")
