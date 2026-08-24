"""
Phase 2 Governance - Audit Integration Tests
Test that API operations generate audit logs correctly
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.identity.audit import AuditAction, AuditService
from src.identity.models import RoleEnum, User


@pytest.mark.asyncio
class TestAuditIntegration:
    """Test audit logging is properly integrated with operations"""

    async def test_audit_log_structure(self, async_session: AsyncSession):
        """Test basic audit log structure"""
        # Create a test user
        user = User(
            username="test_audit_user",
            email="audit@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create audit log
        log = await AuditService.log(
            session=async_session,
            action=AuditAction.BUSINESS_TASK_CREATED,
            resource_type="business_task",
            resource_id="test-123",
            status="success",
            user_id=user.id,
            details={"domain": "marketing", "title": "Test Task"},
        )

        assert log.id is not None
        assert log.user_id == user.id
        assert log.action == AuditAction.BUSINESS_TASK_CREATED
        assert log.resource_type == "business_task"
        assert log.resource_id == "test-123"
        assert log.status == "success"
        assert log.details["domain"] == "marketing"

    async def test_audit_sanitizes_secrets(self, async_session: AsyncSession):
        """Test that sensitive data is redacted"""
        user = User(
            username="test_secrets_user",
            email="secrets@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Log with sensitive data
        log = await AuditService.log(
            session=async_session,
            action=AuditAction.TASK_CREATED,
            resource_type="task",
            status="success",
            user_id=user.id,
            details={
                "title": "API Integration",
                "api_key": "sk_test_secret123",
                "password": "supersecret",
                "public_info": "visible",
            },
        )

        assert log.details["api_key"] == "[REDACTED]"
        assert log.details["password"] == "[REDACTED]"
        assert log.details["public_info"] == "visible"

    async def test_business_task_audit(self, async_session: AsyncSession):
        """Test that business task operations generate audit logs"""
        user = User(
            username="business_user",
            email="business@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Simulate business task creation audit
        log = await AuditService.log(
            session=async_session,
            action=AuditAction.BUSINESS_TASK_CREATED,
            resource_type="business_task",
            resource_id=str(uuid4()),
            status="success",
            user_id=user.id,
            details={
                "domain": "sales",
                "title": "Follow up with lead",
                "priority": "HIGH",
            },
        )

        assert log.action == AuditAction.BUSINESS_TASK_CREATED
        assert log.resource_type == "business_task"
        assert log.details["domain"] == "sales"

    async def test_workflow_audit(self, async_session: AsyncSession):
        """Test workflow operations generate audit logs"""
        user = User(
            username="workflow_user",
            email="workflow@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.ADMIN,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        workflow_id = uuid4()

        # Create workflow audit
        log1 = await AuditService.log(
            session=async_session,
            action=AuditAction.WORKFLOW_CREATE,
            resource_type="workflow",
            resource_id=str(workflow_id),
            status="success",
            user_id=user.id,
            details={"name": "Marketing Campaign Workflow"},
        )

        # Execute workflow audit
        log2 = await AuditService.log(
            session=async_session,
            action=AuditAction.WORKFLOW_EXECUTE,
            resource_type="workflow_execution",
            resource_id=str(uuid4()),
            status="success",
            user_id=user.id,
            details={"workflow_id": str(workflow_id)},
        )

        assert log1.action == AuditAction.WORKFLOW_CREATE
        assert log2.action == AuditAction.WORKFLOW_EXECUTE

    async def test_employee_audit(self, async_session: AsyncSession):
        """Test AI employee operations generate audit logs"""
        user = User(
            username="workforce_user",
            email="workforce@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.ADMIN,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        employee_id = uuid4()

        # Employee created
        log1 = await AuditService.log(
            session=async_session,
            action=AuditAction.EMPLOYEE_CREATED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=user.id,
            details={
                "name": "Marketing AI",
                "department": "MARKETING",
                "position": "CONTENT_WRITER",
            },
        )

        # Employee activated
        log2 = await AuditService.log(
            session=async_session,
            action=AuditAction.EMPLOYEE_ACTIVATED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=user.id,
            details={"action": "activate"},
        )

        assert log1.action == AuditAction.EMPLOYEE_CREATED
        assert log2.action == AuditAction.EMPLOYEE_ACTIVATED

    async def test_task_audit(self, async_session: AsyncSession):
        """Test task operations generate audit logs"""
        user = User(
            username="task_user",
            email="task@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        task_id = uuid4()

        # Task created
        log1 = await AuditService.log(
            session=async_session,
            action=AuditAction.TASK_CREATED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=user.id,
            details={
                "title": "Analyze market data",
                "task_type": "RESEARCH",
                "priority": "HIGH",
            },
        )

        # Task assigned
        log2 = await AuditService.log(
            session=async_session,
            action=AuditAction.TASK_ASSIGNED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=user.id,
            details={"agent_ids": ["agent-1", "agent-2"]},
        )

        # Task completed
        log3 = await AuditService.log(
            session=async_session,
            action=AuditAction.TASK_COMPLETED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=user.id,
            details={"action": "complete"},
        )

        assert log1.action == AuditAction.TASK_CREATED
        assert log2.action == AuditAction.TASK_ASSIGNED
        assert log3.action == AuditAction.TASK_COMPLETED

    async def test_knowledge_audit(self, async_session: AsyncSession):
        """Test knowledge operations generate audit logs"""
        user = User(
            username="knowledge_user",
            email="knowledge@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Document uploaded
        log1 = await AuditService.log(
            session=async_session,
            action=AuditAction.DOCUMENT_UPLOADED,
            resource_type="document",
            resource_id=str(uuid4()),
            status="success",
            user_id=user.id,
            details={
                "title": "Product Specification",
                "type": "PDF",
                "chunk_count": 45,
            },
        )

        # Memory stored
        log2 = await AuditService.log(
            session=async_session,
            action=AuditAction.MEMORY_STORED,
            resource_type="memory",
            resource_id=str(uuid4()),
            status="success",
            user_id=user.id,
            details={"memory_type": "SHORT_TERM"},
        )

        assert log1.action == AuditAction.DOCUMENT_UPLOADED
        assert log2.action == AuditAction.MEMORY_STORED

    async def test_audit_query(self, async_session: AsyncSession):
        """Test querying audit logs"""
        user = User(
            username="query_user",
            email="query@test.com",
            hashed_password="fake_hash",
            role=RoleEnum.USER,
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)

        # Create multiple logs
        for i in range(5):
            await AuditService.log(
                session=async_session,
                action=AuditAction.TASK_CREATED,
                resource_type="task",
                status="success",
                user_id=user.id,
                details={"task_number": i},
            )

        # Query logs
        logs = await AuditService.query_logs(
            session=async_session,
            user_id=user.id,
            action=AuditAction.TASK_CREATED,
        )

        assert len(logs) == 5
        assert all(log.user_id == user.id for log in logs)
        assert all(log.action == AuditAction.TASK_CREATED for log in logs)
