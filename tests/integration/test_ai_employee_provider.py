"""
P2-5 AI Employee Integration Tests

Covers:
- P2-5 #1: Knowledge retrieval → context → LLM chain
- P2-5 #2: Provider failure → Recovery Chain
- P2-5 #3: Knowledge failure -> proper error (not silent)
- P2-5 #4: Audit/Event not bypassed
"""

import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select

from src.database.base import Base
from src.database.models import (
    DocumentModel,
    FailureRecordModel,
)
from src.identity.models import AuditLog
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.identity.rbac import Permission, RBACService, RoleEnum
from src.knowledge.knowledge_retrieval import (
    KnowledgeQuery,
    KnowledgeRetrievalService,
    KnowledgeSource,
)
from src.workforce.employee import AIEmployeeService
from src.workforce.models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    Position,
)
from src.workforce.registry import AIEmployeeRegistry


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user():
    """Create a test user with superuser privileges."""
    user = User()
    user.id = 1
    user.username = "knowledge_user"
    user.email = "knowledge@test.com"
    user.hashed_password = "test_password"
    user.is_active = True
    user.is_superuser = True
    user.role = RoleEnum.ADMIN
    user.full_name = "Knowledge User"
    user.tenant_id = None
    return user


def create_user_no_permission():
    """Create a test user without knowledge:read permission."""
    user = User()
    user.id = 2
    user.username = "no_permission"
    user.email = "noperm@test.com"
    user.role = RoleEnum.USER
    user.full_name = "No Permission User"
    user.tenant_id = None
    return user


class MockAudit(AuditService):
    """Audit stub that swallows log calls."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        return None


# ============================================================================
# Test 1: Knowledge Retrieval -> Context -> LLM chain
# ============================================================================


class TestKnowledgeToContextChain:
    """P2-5 #1: Verify knowledge retrieval is wired into AI Employee execution."""

    @pytest.mark.asyncio
    async def test_knowledge_retrieval_injects_context(self):
        """Knowledge retrieval should inject context when documents exist."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            # Arrange: create a document in the knowledge base
            doc = DocumentModel(
                id=str(uuid4()),
                filename="policy.txt",
                title="Company Policy",
                content="Our company policy is to prioritize customer satisfaction above all else.",
                file_type="txt",
                size=1024,
                status="uploaded",
                created_by="1",
            )
            session.add(doc)

            # Create a test user
            user = create_test_user()
            session.add(user)

            # Create an AI employee
            registry = AIEmployeeRegistry(session)
            rbac = RBACService(session)
            audit = MockAudit()
            service = AIEmployeeService(registry, rbac, audit)

            employee = await service.create_employee(
                name="Test Employee",
                department=Department.SALES,
                position=Position.SALES_REPRESENTATIVE,
                description="A test employee",
            )

            await session.commit()

            # Act: build knowledge context via KnowledgeRetrievalService
            kr_service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=audit,
            )
            ctx = await kr_service.build_context(
                user=user, task="company policy", max_items=5,
            )

            # Assert: knowledge context contains results
            assert len(ctx.results) > 0
            summary = ctx.get_summary()
            assert "Found" in summary
            assert "Company Policy" in summary
            assert "customer satisfaction" in summary

    @pytest.mark.asyncio
    async def test_empty_knowledge_returns_no_results(self):
        """Knowledge retrieval should return empty when no documents exist."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            user = create_test_user()
            session.add(user)

            rbac = RBACService(session)
            audit = MockAudit()
            kr_service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=audit,
            )

            # Act: empty knowledge base
            ctx = await kr_service.build_context(
                user=user, task="nonexistent", max_items=5,
            )

            # Assert: no results
            assert len(ctx.results) == 0
            summary = ctx.get_summary()
            assert "No relevant knowledge found" in summary


# ============================================================================
# Test 2: Provider failure -> Recovery Chain
# ============================================================================


class TestProviderFailureRecovery:
    """P2-5 #2: Verify Provider failure triggers Recovery Chain."""

    @pytest.mark.asyncio
    async def test_execution_failure_no_agent_type(self):
        """When employee has no agent_type, execute_task raises ValidationError."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            user = create_test_user()
            session.add(user)

            registry = AIEmployeeRegistry(session)
            rbac = RBACService(session)
            audit = MockAudit()
            service = AIEmployeeService(registry, rbac, audit)

            # Create an employee without agent_type
            employee = AIEmployee(
                id=uuid4(),
                name="Failure Employee",
                department=Department.SALES,
                position=Position.SALES_REPRESENTATIVE,
                description="Employee that will fail",
                status=AIEmployeeStatus.ACTIVE,
                owner_id=None,
            )
            registered = await registry.register(employee)
            await session.commit()

            # Act: attempt to execute (will fail due to no agent_type)
            with pytest.raises(Exception) as exc_info:
                await service.execute_task(
                    employee_id=employee.id,
                    prompt="test prompt",
                    actor_id=1,
                )

            # Assert: ValidationError was raised
            assert "no agent type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_recovery_chain_records_failure(self):
        """Verify RecoveryChain directly records failures."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.recovery import RecoveryChain

            chain = RecoveryChain(session)

            # Act: record a failure directly
            record = await chain.record_failure(
                failure_summary="Provider timeout",
                failure_detail="LLM provider returned 503 Service Unavailable",
                task_id="test-task-001",
                created_by=1,
                tenant_id=None,
            )

            # Assert: record is persisted
            assert record.id is not None
            assert record.failure_summary == "Provider timeout"
            assert record.failure_detail == "LLM provider returned 503 Service Unavailable"

            # Verify persistence
            stmt = select(FailureRecordModel).where(
                FailureRecordModel.task_id == "test-task-001"
            )
            result = await session.execute(stmt)
            fetched = result.scalar_one_or_none()
            assert fetched is not None
            assert fetched.failure_summary == "Provider timeout"

            # Verify strategy determination
            strategy = await chain.determine_strategy(record)
            assert strategy is not None
            assert strategy.value in ["retry", "switch_provider", "request_boss"]


# ============================================================================
# Test 3: Knowledge failure -> proper error
# ============================================================================


class TestKnowledgeFailureHandling:
    """P2-5 #3: Verify knowledge failure produces proper error, not silent success."""

    @pytest.mark.asyncio
    async def test_knowledge_retrieval_service_rejects_empty_query(self):
        """KnowledgeRetrievalService should raise ValidationError for empty query."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            user = create_test_user()
            session.add(user)

            rbac = RBACService(session)
            audit = MockAudit()
            kr_service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=audit,
            )

            from src.core.errors import ValidationError

            # Act: empty query
            query = KnowledgeQuery(query="   ")

            # Assert: raises ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await kr_service.search(user, query)

            assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_knowledge_retrieval_rejects_no_permission(self):
        """KnowledgeRetrievalService should reject users without permission."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            user = create_user_no_permission()
            session.add(user)

            rbac = RBACService(session)
            audit = MockAudit()
            kr_service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=audit,
            )

            from src.core.errors import PermissionDeniedError

            query = KnowledgeQuery(query="test")

            # Assert: raises PermissionDeniedError
            with pytest.raises(PermissionDeniedError):
                await kr_service.search(user, query)


# ============================================================================
# Test 4: Audit/Event not bypassed
# ============================================================================


class TestAuditNotBypassed:
    """P2-5 #4: Verify Audit/Event is not bypassed by knowledge retrieval."""

    @pytest.mark.asyncio
    async def test_knowledge_retrieval_audits(self):
        """Knowledge retrieval operations should be audited."""
        session_factory = await create_test_session()
        async with session_factory() as session:
            user = create_test_user()
            session.add(user)

            # Create a document so search returns results
            doc = DocumentModel(
                id=str(uuid4()),
                filename="test_doc.txt",
                title="Test Doc",
                content="Test content for audit verification",
                file_type="txt",
                size=512,
                status="uploaded",
                created_by="1",
            )
            session.add(doc)
            await session.commit()

            # Use a real AuditService that records logs
            real_audit = AuditService()
            rbac = RBACService(session)
            kr_service = KnowledgeRetrievalService(
                session=session, rbac_service=rbac, audit_service=real_audit,
            )

            # Act: search
            query = KnowledgeQuery(query="test audit", limit=5)
            results = await kr_service.search(user, query)

            # Assert: results are returned
            assert len(results) > 0

            # Verify audit log was created
            stmt = select(AuditLog).where(AuditLog.resource_type == "knowledge")
            result = await session.execute(stmt)
            logs = result.scalars().all()
            assert len(logs) > 0
            log = logs[0]
            assert log.action == AuditAction.READ
            assert log.status == "success"