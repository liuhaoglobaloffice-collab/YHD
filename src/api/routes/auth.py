"""
Authentication endpoints (login, register)
"""

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from src.identity.audit import AuditService
from src.identity.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from src.identity.database import get_db_session
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user
    """
    # Check if username exists
    result = await session.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Check if email exists
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Audit log
    await AuditService.log_success(
        session=session,
        action="register",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": user.username, "email": user.email},
    )

    logger.info("user_registered", user_id=user.id, username=user.username)

    return user


@router.post("/token", response_model=TokenResponse)
async def token_endpoint(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Minimal compatibility alias requested by the Phase 1 test contract.

    Produces the same response shape as /auth/login while preserving the
    current route object and authentication pipeline.
    """
    return await login(login_data, session)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    User login
    Returns JWT access token
    """
    # Get user
    result = await session.execute(select(User).where(User.username == login_data.username))
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(login_data.password, user.hashed_password):
        # Audit failed login
        await AuditService.log_failure(
            session=session,
            action="login",
            resource_type="user",
            error_message="Invalid credentials",
            details={"username": login_data.username},
        )

        logger.warning("login_failed", username=login_data.username)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        await AuditService.log_denied(
            session=session,
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            reason="User is inactive",
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Update last login
    user.last_login = datetime.now(UTC)
    await session.commit()

    # Create access token
    # JWT 标准要求 sub 必须是字符串，同时添加 role 字段供权限检查
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    # Audit successful login
    await AuditService.log_success(
        session=session,
        action="login",
        resource_type="user",
        user_id=user.id,
        details={"username": user.username},
    )

    logger.info("login_success", user_id=user.id, username=user.username)

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information
    """
    return current_user
