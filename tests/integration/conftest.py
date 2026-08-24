"""
Integration Tests Fixtures

Common fixtures for integration tests across different modules.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.identity.auth import create_access_token
from src.identity.models import User
from src.main import app


@pytest.fixture
async def async_client():
    """创建未认证的 async HTTP 客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def admin_headers(admin_user: User) -> dict:
    """创建 admin 用户的认证 headers"""
    token = create_access_token({"sub": admin_user.username, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def regular_user_headers(regular_user: User) -> dict:
    """创建 regular 用户的认证 headers"""
    token = create_access_token({"sub": regular_user.username, "role": "user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_headers(test_user: User) -> dict:
    """创建 viewer 用户的认证 headers"""
    token = create_access_token({"sub": test_user.username, "role": "viewer"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_user(test_user: User) -> User:
    """Alias for test_user as viewer"""
    return test_user
