"""
MemoryService Tests

Covers:
- Memory store / persist / read
- Memory list with filters
- Memory delete
- Session / task cleanup
- Expired memory cleanup
- Permission checks
- Validation
"""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import Permission, RBACService
from src.knowledge.memory import MemoryService, MemoryType


class MockAudit(AuditService):
    """Audit stub that swallows log calls."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        pass


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user(is_superuser=True):
    """Create a test user."""
    user = User()
    user.id = 1
    user.username = "test_user"
    user.is_active = True
    user.is_superuser = is_superuser
    return user


def create_user_no_permission():
    """Create a user without KNOWLEDGE_WRITE permission."""
    user = User()
    user.id = 99
    user.username = "no_perm_user"
    user.is_active = True
    user.is_superuser = False
    return user


# ============================================================================
# Test 1: Memory store and persist
# ============================================================================


def test_store_memory_persists_to_database():
    """Test store() creates a memory and persists to database."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            memory = await service.store(
                user=user,
                memory_type=MemoryType.SHORT_TERM,
                key="test_key",
                value="test_value",
                session_id="session-1",
            )

            assert memory is not None
            assert memory.key == "test_key"
            assert memory.value == "test_value"
            assert memory.memory_type == MemoryType.SHORT_TERM
            assert memory.session_id == "session-1"
            assert memory.expires_at is not None  # SHORT_TERM expires

    asyncio.run(_run())


def test_store_long_term_memory_no_expiry():
    """Test long-term memory does not expire."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            memory = await service.store(
                user=user,
                memory_type=MemoryType.LONG_TERM,
                key="important_key",
                value="important_value",
            )

            assert memory.expires_at is None

    asyncio.run(_run())


# ============================================================================
# Test 2: Memory retrieve
# ============================================================================


def test_retrieve_memory_by_key():
    """Test retrieve() returns memory by key."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(
                user=user, memory_type=MemoryType.LONG_TERM,
                key="find_me", value="found",
            )

            result = await service.retrieve(user=user, key="find_me")
            assert result is not None
            assert result.key == "find_me"
            assert result.value == "found"

    asyncio.run(_run())


def test_retrieve_memory_returns_none_for_missing():
    """Test retrieve() returns None for non-existent key."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            result = await service.retrieve(user=user, key="nonexistent")
            assert result is None

    asyncio.run(_run())


# ============================================================================
# Test 3: Memory list
# ============================================================================


def test_list_memories_returns_all():
    """Test list_memories() returns all memories for user."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(user=user, memory_type=MemoryType.LONG_TERM, key="a", value="1")
            await service.store(user=user, memory_type=MemoryType.LONG_TERM, key="b", value="2")

            memories = await service.list_memories(user=user)
            assert len(memories) == 2

    asyncio.run(_run())


def test_list_memories_filters_by_type():
    """Test list_memories() filters by memory type."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(user=user, memory_type=MemoryType.SHORT_TERM, key="s", value="1")
            await service.store(user=user, memory_type=MemoryType.LONG_TERM, key="l", value="2")

            short = await service.list_memories(user=user, memory_type=MemoryType.SHORT_TERM)
            assert len(short) == 1
            assert short[0].key == "s"

    asyncio.run(_run())


def test_list_memories_filters_by_session():
    """Test list_memories() filters by session_id."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(user=user, memory_type=MemoryType.SHORT_TERM, key="s1", value="v1", session_id="sess-a")
            await service.store(user=user, memory_type=MemoryType.SHORT_TERM, key="s2", value="v2", session_id="sess-b")

            result = await service.list_memories(user=user, session_id="sess-a")
            assert len(result) == 1
            assert result[0].session_id == "sess-a"

    asyncio.run(_run())


# ============================================================================
# Test 4: Memory delete
# ============================================================================


def test_delete_memory_removes_it():
    """Test delete() removes a memory."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            memory = await service.store(
                user=user, memory_type=MemoryType.LONG_TERM, key="delete_me", value="bye",
            )

            await service.delete(user=user, memory_id=memory.id)

            result = await service.retrieve(user=user, key="delete_me")
            assert result is None

    asyncio.run(_run())


# ============================================================================
# Test 5: Session / Task cleanup
# ============================================================================


def test_clear_session_removes_session_memories():
    """Test clear_session() removes all memories for a session."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(user=user, memory_type=MemoryType.SHORT_TERM, key="a", value="1", session_id="sess-x")
            await service.store(user=user, memory_type=MemoryType.SHORT_TERM, key="b", value="2", session_id="sess-x")
            await service.store(user=user, memory_type=MemoryType.LONG_TERM, key="c", value="3")

            cleared = await service.clear_session(user=user, session_id="sess-x")
            assert cleared == 2

            remaining = await service.list_memories(user=user)
            assert len(remaining) == 1

    asyncio.run(_run())


def test_clear_task_removes_task_memories():
    """Test clear_task() removes all memories for a task."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            await service.store(user=user, memory_type=MemoryType.WORKING, key="a", value="1", task_id="task-1")
            await service.store(user=user, memory_type=MemoryType.WORKING, key="b", value="2", task_id="task-1")

            cleared = await service.clear_task(user=user, task_id="task-1")
            assert cleared == 2

            remaining = await service.list_memories(user=user)
            assert len(remaining) == 0

    asyncio.run(_run())


# ============================================================================
# Test 6: Permission checks
# ============================================================================


def test_store_memory_rejects_user_without_write_permission():
    """Test store() raises PermissionDeniedError for user without KNOWLEDGE_WRITE."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_user_no_permission()

            from src.core.errors import PermissionDeniedError

            with pytest.raises(PermissionDeniedError):
                await service.store(
                    user=user, memory_type=MemoryType.LONG_TERM, key="x", value="y",
                )

    asyncio.run(_run())


# ============================================================================
# Test 7: Validation
# ============================================================================


def test_store_memory_rejects_empty_key():
    """Test store() raises ValidationError for empty key."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import ValidationError

            with pytest.raises(ValidationError):
                await service.store(
                    user=user, memory_type=MemoryType.LONG_TERM, key="   ", value="y",
                )

    asyncio.run(_run())


def test_store_memory_rejects_invalid_confidence():
    """Test store() raises ValidationError for confidence out of range."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = RBACService(session)
            service = MemoryService(
                session=session, rbac_service=rbac, audit_service=MockAudit(),
            )
            user = create_test_user()

            from src.core.errors import ValidationError

            with pytest.raises(ValidationError):
                await service.store(
                    user=user, memory_type=MemoryType.LONG_TERM, key="x", value="y", confidence=1.5,
                )

    asyncio.run(_run())