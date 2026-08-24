"""
Performance Test Configuration
"""

import pytest


@pytest.fixture
async def test_session():
    """测试数据库会话"""
    # 使用内存数据库进行性能测试
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
def admin_user():
    """管理员用户"""
    from src.identity.models import RoleEnum, User

    return User(
        id=1,
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
