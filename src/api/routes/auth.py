"""
Authentication endpoints (login, register)
"""

from datetime import UTC, datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.schemas import LoginRequest, TokenResponse, UserCreate, UserDetailResponse, UserResponse
from src.identity.audit import AuditService
from src.identity.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from src.identity.database import get_db_session
from src.identity.models import AccountType, RoleEnum, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterSubRequest(BaseModel):
    """子账号自助注册申请（待主账号审核）。"""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)


@router.get("/owner-info")
async def get_owner_info(
    session: AsyncSession = Depends(get_db_session),
):
    """返回系统中主账号信息，供子账号注册页面显示。"""
    result = await session.execute(
        select(User).where(User.account_type == AccountType.OWNER).limit(1)
    )
    owner = result.scalar_one_or_none()
    if not owner:
        return {"has_owner": False, "owner_username": None}
    return {
        "has_owner": True,
        "owner_username": owner.username,
        "owner_email": owner.email,
    }


@router.post("/register-sub", status_code=status.HTTP_201_CREATED)
async def register_sub_account(
    request: RegisterSubRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """子账号自助注册：关联到主账号，状态为待审核，主账号同意后方可登录。"""
    # 用户名唯一
    result = await session.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # 自动找到第一个主账号作为归属
    result = await session.execute(
        select(User).where(User.account_type == AccountType.OWNER).limit(1)
    )
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系统中没有主账号，无法注册子账号",
        )

    # 自动生成邮箱
    auto_email = f"{request.username}@example.com"

    user = User(
        username=request.username,
        email=auto_email,
        hashed_password=hash_password(request.password),
        role=RoleEnum.VIEWER,
        account_type=AccountType.SUB,
        parent_user_id=owner.id,
        tenant_id=owner.tenant_id,
        is_active=False,  # 待主账号审核通过后启用
        approval_status="pending",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await AuditService.log_success(
        session=session,
        action="register_sub_pending",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": user.username, "owner_id": owner.id},
    )
    logger.info("sub_account_registered_pending", user_id=user.id, owner_id=owner.id)

    return {
        "id": user.id,
        "username": user.username,
        "status": "pending",
        "owner_username": owner.username,
        "message": f"申请已提交，等待主账号「{owner.username}」审核通过后即可登录",
    }


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

    # 子账号审批拦截：自助注册的子账号需主账号审核通过后才能登录
    if user.account_type == AccountType.SUB and user.approval_status == "pending":
        await AuditService.log_denied(
            session=session,
            action="login",
            resource_type="user",
            resource_id=str(user.id),
            reason="Sub-account awaiting owner approval",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号待主账号审核，请等待主账号通过后再登录",
        )
    if user.account_type == AccountType.SUB and user.approval_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="子账号申请已被拒绝，请联系主账号",
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


@router.get("/me", response_model=UserDetailResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information (含账号类型，用于主/子账号前端分流)
    """
    return current_user
