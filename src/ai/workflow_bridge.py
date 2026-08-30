"""
Workflow Bridge - Phase 3.1 AI Brain Core

Connects AI Brain to existing Workflow Engine.
Converts AI task plans into executable workflows.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..identity.models import User
from ..tasks.models import TaskPriority, TaskType
from ..tasks.service import TaskService
from ..workflow.models import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType
from ..workflow.service import WorkflowService
from .models import AgentAssignment, TaskDecomposition

logger = logging.getLogger(__name__)


class WorkflowBridge:
    """
    Bridge between AI Brain and Workflow Engine.

    Responsibilities:
    - Convert AI task plans to Workflow definitions
    - Create workflow steps from tasks
    - Submit workflows to Workflow Engine
    - Map agent assignments to task assignments
    """

    def __init__(
        self,
        session: AsyncSession,
        workflow_service: Optional[WorkflowService] = None,
        task_service: Optional[TaskService] = None,
    ):
        self.session = session
        self.workflow_service = workflow_service or WorkflowService(session)
        self.task_service = task_service or TaskService(session)
        logger.info("WorkflowBridge initialized")

    async def create_workflow_from_plan(
        self,
        plan: TaskDecomposition,
        assignments: List[AgentAssignment],
        user: User,
        command_id: Optional[UUID] = None,
    ) -> Workflow:
        """
        Convert AI task plan to Workflow definition.

        Args:
            plan: Task decomposition from IntelligentPlanner
            assignments: Agent assignments from AgentRouter
            user: User creating the workflow
            command_id: Optional CEO command ID for tracking

        Returns:
            Created Workflow
        """
        # Validate plan has tasks
        if not plan.tasks:
            raise ValueError("Cannot create workflow from empty task plan")

        # Convert plan tasks to workflow steps
        steps = self._create_workflow_steps(plan, assignments)

        # Generate workflow name
        workflow_name = f"AI Brain: {plan.goal}"
        if len(workflow_name) > 100:
            workflow_name = workflow_name[:97] + "..."

        # Create workflow definition
        workflow = await self.workflow_service.create_workflow(
            name=workflow_name,
            description=f"Generated from CEO command: {plan.goal}",
            steps=steps,
            user=user,
            status=WorkflowStatus.DRAFT,
            tags=["ai_brain", "auto_generated"],
            metadata={
                "command_id": str(command_id) if command_id else None,
                "goal": plan.goal,
                "execution_order": plan.execution_order,
                "estimated_duration_minutes": plan.estimated_duration_minutes,
                "dependencies": plan.dependencies,
                "task_count": len(plan.tasks),
            },
        )

        # Handle None result
        if workflow is None:
            raise ValueError("Failed to create workflow")

        logger.info(
            f"Created workflow from AI plan: {workflow.workflow_id}, "
            f"steps={len(steps)}, goal='{plan.goal}'"
        )

        return workflow

    def _create_workflow_steps(
        self, plan: TaskDecomposition, assignments: List[AgentAssignment]
    ) -> List[Dict]:
        """
        Convert plan tasks to workflow step definitions.

        输出格式与 WorkflowService._dict_to_step / WorkflowExecutor 兼容：
        step_id / step_type / name / task_type / task_config（含 employee_id
        员工分配与 input_data.prompt，供 TaskExecutor 真实执行）。
        """
        assignment_map = {str(a.task_id): a for a in assignments}

        steps = []
        for idx, task in enumerate(plan.tasks):
            task_id = task["task_id"]
            assignment = assignment_map.get(task_id)
            agent_type = task.get("agent_type", "business")

            task_type = self._map_agent_to_task_type(agent_type)
            description = task.get("description", task["name"])

            step = {
                "step_id": f"step-{idx + 1}-{task_id[:8]}",
                "step_type": WorkflowStepType.TASK.value,
                "name": task["name"],
                "description": description,
                "task_type": task_type,
                "task_config": {
                    "description": description,
                    "task_type": task_type,
                    "priority": "medium",
                    # WorkflowExecutor 从 task_config.employee_id 读取员工分配
                    "employee_id": (
                        str(assignment.employee_id)
                        if assignment and assignment.employee_id
                        else None
                    ),
                    "input_data": {
                        "prompt": f"{task['name']}\n\n{description}",
                    },
                },
            }

            steps.append(step)

        return steps

    def _map_agent_to_task_type(self, agent_type: str) -> str:
        """将计划任务的 agent_type 映射为 TaskType 合法值。"""
        mapping = {
            "research": TaskType.RESEARCH.value,
            "marketing": TaskType.MARKETING.value,
            "sales": TaskType.SALES.value,
            "business": TaskType.GENERAL.value,
            "ceo_assistant": TaskType.REPORTING.value,
        }
        return mapping.get(agent_type, TaskType.GENERAL.value)

    async def execute_workflow(
        self,
        workflow: Workflow,
        user: User,
    ) -> UUID:
        """
        Submit workflow for execution via Workflow Engine.

        Args:
            workflow: Workflow to execute
            user: User executing the workflow

        Returns:
            Workflow execution ID (for tracking)

        Note:
            Actual execution is handled by WorkflowExecutor (Stage 5).
            This method just submits the workflow for execution.
        """
        # Update workflow status to ACTIVE
        workflow.status = WorkflowStatus.ACTIVE
        await self.session.commit()

        logger.info(
            f"Submitted workflow for execution: {workflow.workflow_id}, " f"name='{workflow.name}'"
        )

        # Return workflow ID (execution tracking happens in Workflow Executor)
        # Future: Return WorkflowExecution ID from executor
        return workflow.workflow_id

    async def create_task_from_step(
        self,
        step: WorkflowStep,
        workflow_id: UUID,
        user: User,
    ):
        """
        Create Task from workflow step (for step execution).

        This is called by WorkflowExecutor when executing workflow steps.
        Bridges AI Brain workflow to Task System.
        """
        # Extract config
        config = step.config or {}
        agent_type = config.get("agent_type", "business")
        employee_id = config.get("employee_id")

        # Determine task type
        # All workflow tasks are general tasks since TaskType.BUSINESS_TASK doesn't exist
        task_type = TaskType.GENERAL

        # Create task
        task = await self.task_service.create_task(
            title=step.name,
            description=step.description or step.name,
            task_type=task_type,
            user=user,
            priority=TaskPriority.MEDIUM,
            workflow_id=workflow_id,
            metadata={
                "step_id": str(step.step_id),
                "agent_type": agent_type,
                "employee_id": employee_id,
                "constraints": config.get("constraints", []),
            },
        )

        logger.info(
            f"Created task from workflow step: {task.task_id}, "
            f"step='{step.name}', agent={agent_type}"
        )

        return task
