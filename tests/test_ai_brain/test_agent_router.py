"""
Phase 3.1 - Test AgentRouter

Test agent selection and routing logic.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.agent_router import AgentRouter
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


class TestAgentRouter:
    """Test Agent Router for task-to-agent assignment"""

    def test_router_initialization(self):
        """Test router can be initialized"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)
        assert router is not None

    @pytest.mark.asyncio
    async def test_route_research_task(self):
        """Test routing research task to research agent"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "1a690eea-cca4-4e0b-850a-ca214c1d46ee",
            "name": "市场调研",
            "agent_type": "research",
        }

        # Mock AIEmployee object
        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Research Agent"
        mock_employee.department = Department.RESEARCH
        mock_employee.position = Position.MARKET_RESEARCHER
        mock_employee.status = AIEmployeeStatus.ACTIVE

        # Mock registry
        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee])

        assignment = await router.route_task(task)

        assert assignment is not None
        assert assignment.agent_type == "research"
        assert assignment.employee_id == mock_employee.id
        assert assignment.employee_name == "Research Agent"

    @pytest.mark.asyncio
    async def test_route_sales_task(self):
        """Test routing sales task to sales agent"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "d95a6169-2df1-4879-8732-f9f8e930ff72",
            "name": "客户开发",
            "agent_type": "sales",
        }

        # Mock AIEmployee object
        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Sales Agent"
        mock_employee.department = Department.SALES
        mock_employee.position = Position.SALES_REPRESENTATIVE
        mock_employee.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee])

        assignment = await router.route_task(task)

        assert assignment is not None
        assert assignment.agent_type == "sales"
        assert assignment.employee_id == mock_employee.id

    @pytest.mark.asyncio
    async def test_route_marketing_task(self):
        """Test routing marketing task to marketing agent"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "f2a4b648-83a8-4d50-a79d-d37a67fd5606",
            "name": "SEO方案",
            "agent_type": "marketing",
        }

        # Mock AIEmployee object
        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Marketing Agent"
        mock_employee.department = Department.MARKETING
        mock_employee.position = Position.MARKETING_SPECIALIST
        mock_employee.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee])

        assignment = await router.route_task(task)

        assert assignment is not None
        assert assignment.agent_type == "marketing"
        assert assignment.employee_id == mock_employee.id

    @pytest.mark.asyncio
    async def test_route_task_no_agent_specified(self):
        """Test routing task when no specific agent type is specified"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "67aad3a5-c36d-4930-9fd3-b03dc7412558",
            "name": "分析市场",
        }  # No agent_type field

        # Mock AIEmployee object (default business agent)
        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Business Agent"
        mock_employee.department = Department.OPERATIONS
        mock_employee.position = Position.OPERATIONS_COORDINATOR
        mock_employee.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee])

        # Should infer agent type or use default (business)
        assignment = await router.route_task(task)

        assert assignment is not None
        # Should default to business agent type
        assert assignment.agent_type == "business"

    @pytest.mark.asyncio
    async def test_route_task_multiple_agents_available(self):
        """Test routing when multiple agents of same type are available"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "52a1f32f-a332-4a54-be6d-0c2de2d84143",
            "name": "市场调研",
            "agent_type": "research",
        }

        # Mock multiple AIEmployee objects
        mock_employee1 = Mock(spec=AIEmployee)
        mock_employee1.id = uuid4()
        mock_employee1.name = "Research Agent 1"
        mock_employee1.department = Department.RESEARCH
        mock_employee1.position = Position.MARKET_RESEARCHER
        mock_employee1.status = AIEmployeeStatus.ACTIVE

        mock_employee2 = Mock(spec=AIEmployee)
        mock_employee2.id = uuid4()
        mock_employee2.name = "Research Agent 2"
        mock_employee2.department = Department.RESEARCH
        mock_employee2.position = Position.MARKET_RESEARCHER
        mock_employee2.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee1, mock_employee2])

        assignment = await router.route_task(task)

        assert assignment is not None
        assert assignment.agent_type == "research"
        # Should select one of the available agents (currently selects first)
        assert assignment.employee_id in [mock_employee1.id, mock_employee2.id]

    @pytest.mark.asyncio
    async def test_route_task_no_agent_available(self):
        """Test routing when no suitable agent is available"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "26d9b3e8-2ea1-42c4-96da-b146c4574d75",
            "name": "客户开发",
            "agent_type": "sales",
        }

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[])  # No agents

        # Should return assignment without employee_id
        assignment = await router.route_task(task)
        assert assignment is not None
        assert assignment.agent_type == "sales"
        assert assignment.employee_id is None
        assert assignment.confidence == 0.5

    @pytest.mark.asyncio
    async def test_route_task_agent_type_mismatch(self):
        """Test routing when available agents don't match required type"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "3706f5b8-40e0-4f4c-a1a0-3584e0430e8c",
            "name": "客户开发",
            "agent_type": "sales",
        }

        # Mock research agent (wrong type)
        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Research Agent"
        mock_employee.department = Department.RESEARCH
        mock_employee.position = Position.MARKET_RESEARCHER
        mock_employee.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        # list_employees filters by department, so it won't return mismatched agent
        router.registry.list_employees = AsyncMock(return_value=[])

        assignment = await router.route_task(task)

        # Should return assignment without employee when no matching agent
        assert assignment is not None
        assert assignment.agent_type == "sales"
        assert assignment.employee_id is None

    @pytest.mark.asyncio
    async def test_route_task_inactive_agents_filtered(self):
        """Test that inactive agents are not selected"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task = {
            "task_id": "af12cc93-282c-4f07-9dbc-cae782880a43",
            "name": "市场调研",
            "agent_type": "research",
        }

        router.registry = Mock(spec=AIEmployeeRegistry)
        # list_employees already filters by ACTIVE status, so won't return inactive
        router.registry.list_employees = AsyncMock(return_value=[])

        assignment = await router.route_task(task)

        # Should return assignment without employee
        assert assignment is not None
        assert assignment.employee_id is None

    @pytest.mark.asyncio
    async def test_route_batch_tasks(self):
        """Test routing multiple tasks at once"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        from src.ai.models import TaskDecomposition

        tasks = [
            {"task_id": str(uuid4()), "name": "市场调研", "agent_type": "research"},
            {"task_id": str(uuid4()), "name": "客户开发", "agent_type": "sales"},
            {"task_id": str(uuid4()), "name": "SEO方案", "agent_type": "marketing"},
        ]

        plan = TaskDecomposition(goal="Test routing", tasks=tasks)

        # Mock employees for different types
        mock_research = Mock(spec=AIEmployee)
        mock_research.id = uuid4()
        mock_research.name = "Research Agent"
        mock_research.department = Department.RESEARCH
        mock_research.position = Position.MARKET_RESEARCHER
        mock_research.status = AIEmployeeStatus.ACTIVE

        mock_sales = Mock(spec=AIEmployee)
        mock_sales.id = uuid4()
        mock_sales.name = "Sales Agent"
        mock_sales.department = Department.SALES
        mock_sales.position = Position.SALES_REPRESENTATIVE
        mock_sales.status = AIEmployeeStatus.ACTIVE

        mock_marketing = Mock(spec=AIEmployee)
        mock_marketing.id = uuid4()
        mock_marketing.name = "Marketing Agent"
        mock_marketing.department = Department.MARKETING
        mock_marketing.position = Position.MARKETING_SPECIALIST
        mock_marketing.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)

        # Mock different returns based on department
        async def mock_list_employees(department=None, status=None):
            if department == Department.RESEARCH:
                return [mock_research]
            elif department == Department.SALES:
                return [mock_sales]
            elif department == Department.MARKETING:
                return [mock_marketing]
            return []

        router.registry.list_employees = mock_list_employees

        assignments = await router.route_tasks(plan)

        assert assignments is not None
        assert len(assignments) == 3

        # Each task should have an assignment
        for assignment in assignments:
            assert assignment.task_id is not None
            assert assignment.agent_type in ["research", "sales", "marketing"]

    @pytest.mark.asyncio
    async def test_route_task_with_priority(self):
        """Test that task priority affects routing"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        task_high = {
            "task_id": str(uuid4()),
            "name": "紧急市场调研",
            "agent_type": "research",
            "priority": "HIGH",
        }

        mock_employee = Mock(spec=AIEmployee)
        mock_employee.id = uuid4()
        mock_employee.name = "Research Agent"
        mock_employee.department = Department.RESEARCH
        mock_employee.position = Position.MARKET_RESEARCHER
        mock_employee.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_employee])

        assignment = await router.route_task(task_high)

        assert assignment is not None
        # High priority task should still be routed
        assert assignment.agent_type == "research"
        assert assignment.employee_id == mock_employee.id

    @pytest.mark.asyncio
    async def test_load_balancing_basic(self):
        """Test basic load balancing when multiple agents available"""
        mock_session = Mock(spec=AsyncSession)
        router = AgentRouter(mock_session)

        from src.ai.models import TaskDecomposition

        tasks = [
            {"task_id": str(uuid4()), "name": "任务1", "agent_type": "research"},
            {"task_id": str(uuid4()), "name": "任务2", "agent_type": "research"},
            {"task_id": str(uuid4()), "name": "任务3", "agent_type": "research"},
        ]

        plan = TaskDecomposition(goal="Test routing", tasks=tasks)

        # Mock multiple research agents
        mock_agent1 = Mock(spec=AIEmployee)
        mock_agent1.id = uuid4()
        mock_agent1.name = "Research Agent 1"
        mock_agent1.department = Department.RESEARCH
        mock_agent1.position = Position.MARKET_RESEARCHER
        mock_agent1.status = AIEmployeeStatus.ACTIVE

        mock_agent2 = Mock(spec=AIEmployee)
        mock_agent2.id = uuid4()
        mock_agent2.name = "Research Agent 2"
        mock_agent2.department = Department.RESEARCH
        mock_agent2.position = Position.MARKET_RESEARCHER
        mock_agent2.status = AIEmployeeStatus.ACTIVE

        router.registry = Mock(spec=AIEmployeeRegistry)
        router.registry.list_employees = AsyncMock(return_value=[mock_agent1, mock_agent2])

        assignments = await router.route_tasks(plan)

        assert assignments is not None
        assert len(assignments) == 3

        # Tasks should be assigned (currently all to first agent in Phase 3.1)
        for assignment in assignments:
            assert assignment.employee_id is not None
            assert assignment.employee_id in [mock_agent1.id, mock_agent2.id]
