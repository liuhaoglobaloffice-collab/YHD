"""
Agent Router - Phase 3.1 AI Brain Core

Routes tasks to appropriate AI agents/employees.
"""

import logging
from typing import Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..workforce.models import AIEmployeeStatus, Department, Position
from ..workforce.registry import AIEmployeeRegistry
from .models import AgentAssignment, TaskDecomposition

logger = logging.getLogger(__name__)


class AgentRouter:
    """
    Routes tasks to appropriate AI agents/employees.

    Responsibilities:
    - Map task types to agent types
    - Select best available agent/employee
    - Load balancing (future)
    - Fallback selection
    """

    # Agent type to Department/Position mapping
    AGENT_MAPPING = {
        "research": {
            "department": Department.RESEARCH,
            "position": Position.MARKET_RESEARCHER,
        },
        "marketing": {
            "department": Department.MARKETING,
            "position": Position.MARKETING_SPECIALIST,
        },
        "sales": {
            "department": Department.SALES,
            "position": Position.SALES_REPRESENTATIVE,
        },
        "business": {
            "department": Department.OPERATIONS,
            "position": Position.OPERATIONS_COORDINATOR,
        },
        "ceo_assistant": {
            "department": Department.CEO_OFFICE,
            "position": Position.CEO_ASSISTANT,
        },
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = AIEmployeeRegistry(session)
        logger.info("AgentRouter initialized")

    async def route_tasks(self, plan: TaskDecomposition) -> List[AgentAssignment]:
        """
        Route all tasks in plan to specific AI employees.

        Args:
            plan: Task decomposition plan

        Returns:
            List of agent assignments
        """
        assignments = []

        for task in plan.tasks:
            assignment = await self.route_task(task)
            assignments.append(assignment)

        logger.info(f"Routed {len(assignments)} tasks to agents")

        return assignments

    async def route_task(self, task: Dict) -> AgentAssignment:
        """
        Route single task to specific AI employee.

        Args:
            task: Task dictionary with agent_type

        Returns:
            AgentAssignment with selected employee
        """
        agent_type = task.get("agent_type", "business")
        task_id = UUID(task["task_id"])

        # Get department and position for agent type
        mapping = self.AGENT_MAPPING.get(
            agent_type, self.AGENT_MAPPING["business"]  # Default fallback
        )

        # Find available employee
        try:
            employees = await self.registry.list_employees(
                department=mapping["department"], status=AIEmployeeStatus.ACTIVE
            )

            if employees:
                # For Phase 3.1: Select first available
                # Future: Load balancing, performance-based selection
                employee = employees[0]

                assignment = AgentAssignment(
                    task_id=task_id,
                    task_description=task.get("description", task["name"]),
                    agent_type=agent_type,
                    employee_id=employee.id,
                    employee_name=employee.name,
                    department=employee.department.value,
                    position=employee.position.value,
                    confidence=1.0,
                    reason=f"Selected {employee.name} from {mapping['department'].value}",
                )
            else:
                # No employee found, create placeholder assignment
                assignment = AgentAssignment(
                    task_id=task_id,
                    task_description=task.get("description", task["name"]),
                    agent_type=agent_type,
                    confidence=0.5,
                    reason=f"No {agent_type} employee available, will create dynamically",
                )

                logger.warning(
                    f"No {agent_type} employee found for task {task_id}, "
                    "assignment created without employee"
                )

        except Exception as e:
            logger.error(f"Error routing task {task_id}: {e}")
            # Fallback assignment
            assignment = AgentAssignment(
                task_id=task_id,
                task_description=task.get("description", task["name"]),
                agent_type=agent_type,
                confidence=0.0,
                reason=f"Routing error: {str(e)}",
            )

        return assignment

    def get_agent_capability_score(self, agent_type: str, task_constraints: List[str]) -> float:
        """
        Calculate agent capability score for task (future feature).

        Considers:
        - Agent specialization
        - Past performance
        - Current load
        - Task complexity match

        Returns:
            Score 0.0-1.0
        """
        # Phase 3.1: Return 1.0 (no scoring yet)
        # Future: Implement performance-based scoring
        return 1.0
