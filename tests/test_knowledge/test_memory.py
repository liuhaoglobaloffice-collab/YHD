"""
Tests for Memory System
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.identity.models import RoleEnum, User
from src.identity.rbac import Permission
from src.knowledge.memory import (
    Memory,
    MemoryService,
    MemoryType,
)


@pytest.fixture
def regular_user():
    """Regular user fixture"""
    from uuid import uuid4

    return User(
        id=str(uuid4()),
        username="testuser",
        email="user@test.com",
        hashed_password="hashed",
        role=RoleEnum.USER,
        is_active=True,
    )


@pytest.fixture
def mock_rbac():
    """Mock RBAC service"""

    class MockRBAC:
        def has_permission(self, user, permission):
            if permission in [Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE]:
                return True
            return False

        def is_admin(self, user):
            return user.role == "admin"

    return MockRBAC()


@pytest.fixture
def mock_audit():
    """Mock audit service"""

    class MockAudit:
        async def log(self, action, user_id, resource_type, resource_id=None, details=None):
            pass

        async def log_permission_denied(self, user_id, action, resource_type, resource_id=None):
            pass

    return MockAudit()


@pytest_asyncio.fixture
async def async_session():
    """Test database session"""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create tables
    from src.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def memory_service(async_session, mock_rbac, mock_audit):
    """Memory service fixture"""
    return MemoryService(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )


class TestMemory:
    """Test Memory"""

    def test_memory_creation(self):
        """Test memory creation"""
        memory = Memory(
            id="mem1",
            memory_type=MemoryType.SHORT_TERM,
            key="user_preference",
            value="dark_mode",
            user_id="user1",
            session_id="session1",
        )

        assert memory.id == "mem1"
        assert memory.memory_type == MemoryType.SHORT_TERM
        assert memory.key == "user_preference"
        assert memory.value == "dark_mode"

    def test_memory_to_dict(self):
        """Test memory to_dict"""
        memory = Memory(
            id="mem1",
            memory_type=MemoryType.LONG_TERM,
            key="company_name",
            value="Acme Corp",
            user_id="user1",
        )

        data = memory.to_dict()
        assert data["id"] == "mem1"
        assert data["memory_type"] == "long_term"
        assert data["key"] == "company_name"


class TestMemoryService:
    """Test MemoryService"""

    @pytest.mark.asyncio
    async def test_store_short_term_memory(self, memory_service, regular_user):
        """Test storing short-term memory"""
        memory = await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="current_topic",
            value="product_pricing",
            session_id="session1",
        )

        assert memory.memory_type == MemoryType.SHORT_TERM
        assert memory.key == "current_topic"
        assert memory.expires_at is not None

    @pytest.mark.asyncio
    async def test_store_working_memory(self, memory_service, regular_user):
        """Test storing working memory"""
        memory = await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.WORKING,
            key="task_context",
            value={"task": "research", "progress": 50},
            task_id="task1",
        )

        assert memory.memory_type == MemoryType.WORKING
        assert memory.task_id == "task1"
        assert memory.expires_at is not None

    @pytest.mark.asyncio
    async def test_store_long_term_memory(self, memory_service, regular_user):
        """Test storing long-term memory"""
        memory = await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.LONG_TERM,
            key="company_info",
            value={"name": "Acme", "industry": "Tech"},
        )

        assert memory.memory_type == MemoryType.LONG_TERM
        assert memory.expires_at is None  # Long-term doesn't expire

    @pytest.mark.asyncio
    async def test_retrieve_memory(self, memory_service, regular_user):
        """Test retrieving memory"""
        # Store memory
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="test_key",
            value="test_value",
            session_id="session1",
        )

        # Retrieve memory
        memory = await memory_service.retrieve(
            user=regular_user,
            key="test_key",
            session_id="session1",
        )

        assert memory is not None
        assert memory.key == "test_key"
        assert memory.value == "test_value"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_memory(self, memory_service, regular_user):
        """Test retrieving nonexistent memory"""
        memory = await memory_service.retrieve(
            user=regular_user,
            key="nonexistent",
        )

        assert memory is None

    @pytest.mark.asyncio
    async def test_list_memories(self, memory_service, regular_user):
        """Test listing memories"""
        # Store multiple memories
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="key1",
            value="value1",
            session_id="session1",
        )
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.LONG_TERM,
            key="key2",
            value="value2",
        )

        # List all memories
        memories = await memory_service.list_memories(regular_user)
        assert len(memories) >= 2

        # List by type
        short_term = await memory_service.list_memories(
            regular_user,
            memory_type=MemoryType.SHORT_TERM,
        )
        assert all(m.memory_type == MemoryType.SHORT_TERM for m in short_term)

    @pytest.mark.asyncio
    async def test_delete_memory(self, memory_service, regular_user):
        """Test deleting memory"""
        # Store memory
        memory = await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="temp_key",
            value="temp_value",
        )

        # Delete memory
        await memory_service.delete(regular_user, memory.id)

        # Verify deleted (inactive)
        retrieved = await memory_service.retrieve(regular_user, "temp_key")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_clear_session(self, memory_service, regular_user):
        """Test clearing session memories"""
        # Store session memories
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="key1",
            value="value1",
            session_id="session1",
        )
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.SHORT_TERM,
            key="key2",
            value="value2",
            session_id="session1",
        )

        # Clear session
        cleared = await memory_service.clear_session(regular_user, "session1")
        assert cleared == 2

        # Verify cleared
        memories = await memory_service.list_memories(
            regular_user,
            session_id="session1",
        )
        assert len(memories) == 0

    @pytest.mark.asyncio
    async def test_clear_task(self, memory_service, regular_user):
        """Test clearing task memories"""
        # Store task memories
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.WORKING,
            key="key1",
            value="value1",
            task_id="task1",
        )
        await memory_service.store(
            user=regular_user,
            memory_type=MemoryType.WORKING,
            key="key2",
            value="value2",
            task_id="task1",
        )

        # Clear task
        cleared = await memory_service.clear_task(regular_user, "task1")
        assert cleared == 2

        # Verify cleared
        memories = await memory_service.list_memories(
            regular_user,
            task_id="task1",
        )
        assert len(memories) == 0

    @pytest.mark.skip(
        reason="Test for old in-memory implementation - Service now uses database repository"
    )
    def test_clean_expired(self, memory_service):
        # Manually create expired memory
        expired_memory = Memory(
            id="expired1",
            memory_type=MemoryType.SHORT_TERM,
            key="expired",
            value="value",
            user_id="user1",
            expires_at=datetime.now(UTC) - timedelta(hours=2),
        )

        memory_service._memories["expired1"] = expired_memory
        memory_service._user_memories["user1"] = ["expired1"]

        # Clean expired
        cleaned = memory_service._clean_expired()
        assert cleaned == 1
        assert not expired_memory.is_active
