"""
Phase 2E Test Fixtures
Provides reusable async test fixtures for database and services
"""

from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base
from src.database.repositories.business import BusinessTaskRepository
from src.database.repositories.knowledge import (
    CompanyBrainEntityRepository,
    DocumentRepository,
    MemoryRepository,
)
from src.database.repositories.task import TaskRepository
from src.database.repositories.workflow import WorkflowRepository
from src.database.repositories.workforce import AIEmployeeRepository

# Import identity models to register them with Base.metadata
# This ensures test database includes identity tables (users, approval_requests, etc.)
from src.identity.models import User


# Load environment for tests
@pytest.fixture(scope="session", autouse=True)
def load_test_env():
    """Load .env file for all tests"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)


@pytest_asyncio.fixture
async def async_engine():
    """Create async test database engine"""
    # Use in-memory SQLite for tests
    test_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(test_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncSession:
    """Create async database session for tests"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def workflow_repo(async_session: AsyncSession) -> WorkflowRepository:
    """Create WorkflowRepository for tests"""
    return WorkflowRepository(async_session)


@pytest_asyncio.fixture
async def task_repo(async_session: AsyncSession) -> TaskRepository:
    """Create TaskRepository for tests"""
    return TaskRepository(async_session)


@pytest_asyncio.fixture
async def employee_repo(async_session: AsyncSession) -> AIEmployeeRepository:
    """Create AIEmployeeRepository for tests"""
    return AIEmployeeRepository(async_session)


@pytest_asyncio.fixture
async def business_repo(async_session: AsyncSession) -> BusinessTaskRepository:
    """Create BusinessTaskRepository for tests"""
    return BusinessTaskRepository(async_session)


@pytest_asyncio.fixture
async def document_repo(async_session: AsyncSession) -> DocumentRepository:
    """Create DocumentRepository for tests"""
    return DocumentRepository(async_session)


@pytest_asyncio.fixture
async def memory_repo(async_session: AsyncSession) -> MemoryRepository:
    """Create MemoryRepository for tests"""
    return MemoryRepository(async_session)


@pytest_asyncio.fixture
async def company_brain_repo(async_session: AsyncSession) -> CompanyBrainEntityRepository:
    """Create CompanyBrainEntityRepository for tests"""
    return CompanyBrainEntityRepository(async_session)


from src.identity.models import RoleEnum


# User Fixtures for Governance Tests
@pytest_asyncio.fixture
async def test_user(async_session: AsyncSession) -> User:
    """Create test user for governance tests"""
    user = User(
        id=1,
        email="user@test.com",
        username="testuser",
        hashed_password="hash",
        role=RoleEnum.USER,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def regular_user(async_session: AsyncSession) -> User:
    """Create regular user (alias for test_user)"""
    user = User(
        id=10,
        email="regular@test.com",
        username="regularuser",
        hashed_password="hash",
        role=RoleEnum.USER,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession) -> User:
    """Create admin user for governance tests"""
    user = User(
        id=2,
        email="admin@test.com",
        username="admin",
        hashed_password="hash",
        role=RoleEnum.ADMIN,
        is_active=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user
