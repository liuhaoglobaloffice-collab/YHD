"""
LiuHao AI OS Y1.0
Test fixtures for Identity Governance tests
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.models import RoleEnum, User


@pytest_asyncio.fixture
async def target_user(async_session: AsyncSession) -> User:
    """Create a target user for governance operations"""
    user = User(
        id=20,
        email="target@test.com",
        username="targetuser",
        hashed_password="hash",
        role=RoleEnum.USER,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user
