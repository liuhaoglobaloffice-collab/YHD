"""
Test CEO Dashboard Service
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agents import AgentType
from src.business.models import (
    BusinessDomain,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.business.registry import BusinessTaskRegistry
from src.ceo.dashboard import CEODashboard
from src.governance.approval import ApprovalService
from src.identity.audit import AuditService
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


@pytest_asyncio.fixture
async def business_registry(async_session: AsyncSession):
    """Fixture: Business registry with sample data."""
    registry = BusinessTaskRegistry(async_session)

    # Add sample task (completed)
    task1 = BusinessTask(
        domain=BusinessDomain.SALES,
        title="Test Task 1",
        status=BusinessTaskStatus.COMPLETED,
        priority=BusinessTaskPriority.HIGH,
        description="Test task 1",
    )
    await registry.register(task1)

    # Add sample task (in progress)
    task2 = BusinessTask(
        domain=BusinessDomain.MARKETING,
        title="Test Task 2",
        status=BusinessTaskStatus.IN_PROGRESS,
        priority=BusinessTaskPriority.MEDIUM,
        description="Test task 2",
    )
    await registry.register(task2)

    return registry


@pytest_asyncio.fixture
async def employee_registry(async_session: AsyncSession):
    """Fixture: Employee registry with sample data."""
    registry = AIEmployeeRegistry(async_session)

    # Add sample employees
    emp1 = AIEmployee(
        name="GPT Agent",
        department=Department.CEO_OFFICE,
        position=Position.CEO_ASSISTANT,
        description="CEO's AI assistant",
        agent_type=AgentType.GPT,
        status=AIEmployeeStatus.ACTIVE,
    )
    await registry.register(emp1)

    return registry


@pytest.fixture
async def approval_service():
    """Fixture: Approval service with sample data."""
    from unittest.mock import AsyncMock


    service = AsyncMock(spec=ApprovalService)
    service.list_requests = AsyncMock(return_value=[])
    return service


@pytest.fixture
async def audit_service():
    """Fixture: Audit service."""
    return AuditService()


@pytest.fixture
async def rbac_service():
    """Fixture: RBAC service (mocked)."""
    from unittest.mock import AsyncMock

    from src.identity.rbac import RBACService

    service = AsyncMock(spec=RBACService)
    service.check_permission = AsyncMock(return_value=True)
    return service


@pytest_asyncio.fixture
async def dashboard(
    business_registry, employee_registry, approval_service, audit_service, rbac_service
):
    """Fixture: CEO Dashboard."""
    return CEODashboard(
        business_registry=business_registry,
        employee_registry=employee_registry,
        approval_service=approval_service,
        audit_service=audit_service,
        rbac_service=rbac_service,
    )


class TestCEODashboard:
    """Test CEODashboard service."""

    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, dashboard):
        """Test dashboard initializes correctly."""
        assert dashboard.business_registry is not None
        assert dashboard.employee_registry is not None

    @pytest.mark.asyncio
    async def test_get_dashboard(self, dashboard):
        """Test get_dashboard returns complete data."""
        user_id = uuid4()
        data = await dashboard.get_dashboard(user_id=user_id)

        assert data.system is not None
        assert data.business is not None
        assert data.ai_team is not None

    @pytest.mark.asyncio
    async def test_get_business_overview(self, dashboard):
        """Test get_business_overview aggregates business data."""
        user_id = uuid4()
        business = await dashboard.get_business_overview(user_id=user_id)

        assert business.total_tasks == 2
        assert business.completed_tasks == 1
        assert business.in_progress_tasks == 1

    @pytest.mark.asyncio
    async def test_get_ai_team_overview(self, dashboard):
        """Test get_ai_team_overview aggregates workforce data."""
        user_id = uuid4()
        ai_team = await dashboard.get_ai_team_overview(user_id=user_id)

        assert ai_team.total_employees == 1
        assert ai_team.active_employees == 1

    @pytest.mark.asyncio
    async def test_dashboard_permission_denied(self, dashboard, rbac_service):
        """Test dashboard blocks unauthorized access."""
        user_id = uuid4()
        rbac_service.check_permission.return_value = False

        with pytest.raises(PermissionError):
            await dashboard.get_dashboard(user_id=user_id)
