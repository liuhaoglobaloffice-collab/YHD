"""
Tests for AI Employee Lifecycle Manager.
"""

from unittest.mock import Mock

import pytest

from src.ai.agents import AgentType
from src.core.errors import ValidationError
from src.workforce.lifecycle import EmployeeLifecycleManager
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


@pytest.fixture
def registry(async_session):
    """Create registry."""
    return AIEmployeeRegistry(async_session)


@pytest.fixture
def rbac_service():
    """Create mock RBAC service."""
    # Mock RBAC service that always allows
    mock = Mock()
    return mock


@pytest.fixture
def audit_service():
    """Create audit service."""
    # Mock audit service
    mock = Mock()
    mock.log = Mock()
    return mock


@pytest.fixture
def lifecycle(registry, rbac_service, audit_service):
    """Create lifecycle manager."""
    return EmployeeLifecycleManager(registry, rbac_service, audit_service)


@pytest.fixture
async def employee(registry):
    """Create and register a sample employee."""
    emp = AIEmployee(
        name="Test Employee",
        department=Department.OPERATIONS,
        position=Position.TASK_MANAGER,
        description="Test",
        agent_type=AgentType.GPT,
        status=AIEmployeeStatus.CREATED,
    )
    return await registry.register(emp)


async def test_activate_employee(lifecycle, employee):
    """Test activating an employee."""
    result = await lifecycle.activate(employee.id)

    assert result.status == AIEmployeeStatus.ACTIVE
    assert result.activated_at is not None


async def test_activate_already_active(lifecycle, employee, registry):
    """Test activating already active employee."""
    await lifecycle.activate(employee.id)

    # Activate again - should be idempotent
    result = await lifecycle.activate(employee.id)
    assert result.status == AIEmployeeStatus.ACTIVE


async def test_activate_without_agent(lifecycle, employee, registry):
    """Test activating employee without agent fails."""
    # Remove agent
    # Mock the get method to return an employee without agent_type
    from unittest.mock import AsyncMock

    original_get = registry.get
    employee_no_agent = employee
    employee_no_agent.agent_type = None
    registry.get = AsyncMock(return_value=employee_no_agent)

    with pytest.raises(ValidationError, match="without assigned agent"):
        await lifecycle.activate(employee.id)

    # Restore original method
    registry.get = original_get


async def test_suspend_active_employee(lifecycle, employee, registry):
    """Test suspending an active employee."""
    # First activate
    await lifecycle.activate(employee.id)

    # Then suspend
    result = await lifecycle.suspend(employee.id, reason="Testing suspension")

    assert result.status == AIEmployeeStatus.SUSPENDED
    assert result.suspended_at is not None
    assert result.metadata.get("suspension_reason") == "Testing suspension"


async def test_retire_employee(lifecycle, employee):
    """Test retiring an employee."""
    # Activate first
    await lifecycle.activate(employee.id)

    # Retire
    result = await lifecycle.retire(employee.id, reason="End of project")

    assert result.status == AIEmployeeStatus.RETIRED
    assert result.retired_at is not None
    assert result.metadata.get("retirement_reason") == "End of project"


async def test_cannot_retire_from_created(lifecycle, employee):
    """Test cannot retire from CREATED status (invalid transition)."""
    # CREATED -> RETIRED is not valid
    with pytest.raises(ValidationError, match="Cannot retire"):
        await lifecycle.retire(employee.id)


def test_can_transition(lifecycle):
    """Test valid state transitions."""
    assert lifecycle.can_transition(AIEmployeeStatus.CREATED, AIEmployeeStatus.ACTIVE)
    assert lifecycle.can_transition(AIEmployeeStatus.ACTIVE, AIEmployeeStatus.SUSPENDED)
    assert not lifecycle.can_transition(AIEmployeeStatus.RETIRED, AIEmployeeStatus.ACTIVE)


def test_lifecycle_state_machine():
    """Test full lifecycle state machine."""
    lifecycle = EmployeeLifecycleManager.__dict__["VALID_TRANSITIONS"]

    # CREATED can go to TRAINING or ACTIVE
    assert AIEmployeeStatus.TRAINING in lifecycle[AIEmployeeStatus.CREATED]
    assert AIEmployeeStatus.ACTIVE in lifecycle[AIEmployeeStatus.CREATED]

    # ACTIVE can go to SUSPENDED or RETIRED
    assert AIEmployeeStatus.SUSPENDED in lifecycle[AIEmployeeStatus.ACTIVE]
    assert AIEmployeeStatus.RETIRED in lifecycle[AIEmployeeStatus.ACTIVE]

    # RETIRED is terminal
    assert len(lifecycle[AIEmployeeStatus.RETIRED]) == 0
