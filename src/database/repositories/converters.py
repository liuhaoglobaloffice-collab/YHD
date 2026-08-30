"""
Model Converters - Phase 2E Circular Import Fix

Converts between domain models (dataclasses) and database models (SQLAlchemy).
Moved from src.database.converters to break circular dependency.

Dependency flow:
    Service → Repository (uses converters) → Database Models

This file only imports:
- Domain models (workflow, tasks, etc.)
- Database models (from database.models)
- No service imports = no circular dependency
"""

from typing import Any, Dict
from uuid import UUID

from src.business.models import (
    BusinessDomain,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)

# Database models
from src.database.models import (
    AIEmployeeModel,
    BusinessTaskModel,
    TaskModel,
    WorkflowExecutionModel,
    WorkflowModel,
)
from src.tasks.models import Task, TaskDependency, TaskPriority, TaskResult, TaskStatus, TaskType

# Domain models
from src.workflow.models import (
    Workflow,
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)
from src.workforce.models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    Position,
)

# ============================================================================
# Workflow Converters
# ============================================================================


def workflow_to_model(workflow: Workflow) -> WorkflowModel:
    """Convert Workflow dataclass to WorkflowModel (SQLAlchemy)"""
    return WorkflowModel(
        id=str(workflow.workflow_id),
        name=workflow.name,
        description=workflow.description,
        created_by=str(workflow.created_by),
        version=1,  # Default version
        tags=workflow.tags,
        enabled=(workflow.status == WorkflowStatus.ACTIVE),
        steps=[_step_to_dict(step) for step in workflow.steps],
        context={
            "status": workflow.status.value,
            "required_permissions": workflow.required_permissions,
            "meta": workflow.metadata,
        },
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def model_to_workflow(model: WorkflowModel) -> Workflow:
    """Convert WorkflowModel (SQLAlchemy) to Workflow dataclass"""
    context = model.context or {}
    status_str = context.get("status", "ACTIVE" if model.enabled else "PAUSED")

    return Workflow(
        workflow_id=UUID(model.id),
        name=model.name,
        description=model.description or "",
        status=WorkflowStatus(status_str),
        steps=[_dict_to_step(step_dict) for step_dict in model.steps],
        created_by=int(model.created_by) if model.created_by.isdigit() else None,
        created_at=model.created_at,
        updated_at=model.updated_at,
        required_permissions=context.get("required_permissions", []),
        tags=model.tags or [],
        metadata=context.get("meta", {}),
    )


def _step_to_dict(step: WorkflowStep) -> Dict[str, Any]:
    """Convert WorkflowStep to dict for JSON storage"""
    return {
        "step_id": step.step_id,
        "step_type": step.step_type.value,
        "name": step.name,
        "description": step.description,
        "task_type": step.task_type,
        "task_config": step.task_config,
        "steps": [_step_to_dict(s) for s in step.steps],
        "condition": step.condition,
        "true_steps": [_step_to_dict(s) for s in step.true_steps],
        "false_steps": [_step_to_dict(s) for s in step.false_steps],
        "loop_condition": step.loop_condition,
        "max_iterations": step.max_iterations,
        "timeout_seconds": step.timeout_seconds,
        "max_retries": step.max_retries,
        "retry_delay_seconds": step.retry_delay_seconds,
        "required_permissions": step.required_permissions,
    }


def _dict_to_step(step_dict: Dict[str, Any]) -> WorkflowStep:
    """Convert dict to WorkflowStep"""
    return WorkflowStep(
        step_id=step_dict["step_id"],
        step_type=WorkflowStepType(step_dict["step_type"]),
        name=step_dict["name"],
        description=step_dict.get("description", ""),
        task_type=step_dict.get("task_type"),
        task_config=step_dict.get("task_config", {}),
        steps=[_dict_to_step(s) for s in step_dict.get("steps", [])],
        condition=step_dict.get("condition"),
        true_steps=[_dict_to_step(s) for s in step_dict.get("true_steps", [])],
        false_steps=[_dict_to_step(s) for s in step_dict.get("false_steps", [])],
        loop_condition=step_dict.get("loop_condition"),
        max_iterations=step_dict.get("max_iterations", 10),
        timeout_seconds=step_dict.get("timeout_seconds"),
        max_retries=step_dict.get("max_retries", 0),
        retry_delay_seconds=step_dict.get("retry_delay_seconds", 5),
        required_permissions=step_dict.get("required_permissions", []),
    )


def workflow_execution_to_model(execution: WorkflowExecution) -> WorkflowExecutionModel:
    """Convert WorkflowExecution dataclass to WorkflowExecutionModel"""
    return WorkflowExecutionModel(
        id=str(execution.execution_id),
        workflow_id=str(execution.workflow_id),
        user_id=str(execution.started_by) if execution.started_by else None,
        status=execution.status.value,
        variables=execution.variables,
        result=execution.result,
        error=execution.error,
        meta=execution.metadata,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )


def model_to_workflow_execution(model: WorkflowExecutionModel) -> WorkflowExecution:
    """Convert WorkflowExecutionModel to WorkflowExecution dataclass"""
    # user_id may be a UUID string or an integer ID; handle both
    started_by = None
    if model.user_id:
        try:
            started_by = UUID(model.user_id)
        except ValueError:
            # Not a valid UUID, store as string (e.g. integer user ID)
            started_by = model.user_id  # type: ignore[assignment]
    return WorkflowExecution(
        execution_id=UUID(model.id),
        workflow_id=UUID(model.workflow_id),
        started_by=started_by,
        status=WorkflowExecutionStatus(model.status),
        variables=model.variables or {},
        result=model.result,
        error=model.error,
        metadata=model.meta or {},
        started_at=model.started_at,
        completed_at=model.completed_at,
    )


# ============================================================================
# Task Converters
# ============================================================================


def task_to_model(task: Task) -> TaskModel:
    """Convert Task dataclass to TaskModel"""
    return TaskModel(
        id=str(task.id),
        title=task.title,
        description=task.description,
        task_type=task.task_type.value,
        status=task.status.value,
        priority=task.priority.value,
        creator_id=str(task.creator_id) if task.creator_id else None,
        assigned_to=[str(a) for a in task.assigned_to] if task.assigned_to else None,
        workflow_id=str(task.workflow_id) if task.workflow_id else None,
        parent_task_id=str(task.parent_task_id) if task.parent_task_id else None,
        dependencies=(
            [{"task_id": str(d.task_id), "type": d.dependency_type} for d in task.dependencies]
            if task.dependencies
            else None
        ),
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        input_data=task.input_data,
        result_data=task.result.output if task.result else None,
        error=task.result.error if task.result else task.error,
        meta=task.metadata,
        tags=task.tags,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        deadline=task.deadline,
    )


def model_to_task(model: TaskModel) -> Task:
    """Convert TaskModel to Task dataclass"""
    # Convert dependencies from list of dicts to list of TaskDependency objects
    dependencies = []
    if model.dependencies:
        for dep_dict in model.dependencies:
            dependencies.append(
                TaskDependency(
                    task_id=UUID(dep_dict["task_id"]),
                    dependency_type=dep_dict.get("type", "finish_to_start"),
                )
            )

    # Convert result_data/error to TaskResult if present
    result = None
    if model.result_data or model.error:
        result = TaskResult(
            success=model.status == TaskStatus.COMPLETED.value,
            output=model.result_data,
            error=model.error,
        )

    return Task(
        id=UUID(model.id),
        title=model.title,
        description=model.description or "",
        task_type=TaskType(model.task_type),
        status=TaskStatus(model.status),
        priority=TaskPriority(model.priority),
        assigned_to=[UUID(a) for a in (model.assigned_to or [])],
        creator_id=UUID(model.creator_id) if model.creator_id else None,
        workflow_id=UUID(model.workflow_id) if model.workflow_id else None,
        parent_task_id=UUID(model.parent_task_id) if model.parent_task_id else None,
        dependencies=dependencies,
        retry_count=model.retry_count or 0,
        max_retries=model.max_retries or 3,
        input_data=model.input_data or {},
        result=result,
        error=model.error,
        metadata=model.meta or {},
        tags=model.tags or [],
        created_at=model.created_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        deadline=model.deadline,
    )


# ============================================================================
# Workforce Converters
# ============================================================================


def employee_to_model(employee: AIEmployee) -> AIEmployeeModel:
    """Convert AIEmployee dataclass to AIEmployeeModel"""
    # Store lifecycle timestamps in metadata
    metadata = employee.metadata.copy()
    if employee.activated_at:
        metadata["activated_at"] = employee.activated_at.isoformat()
    if employee.suspended_at:
        metadata["suspended_at"] = employee.suspended_at.isoformat()
    if employee.retired_at:
        metadata["retired_at"] = employee.retired_at.isoformat()

    # Store statistical fields in metadata
    metadata["tasks_completed"] = employee.tasks_completed
    metadata["tasks_failed"] = employee.tasks_failed
    metadata["total_execution_time_seconds"] = employee.total_execution_time_seconds
    metadata["total_cost_usd"] = employee.total_cost_usd

    return AIEmployeeModel(
        id=str(employee.id),
        name=employee.name,
        department=employee.department.value,
        position=employee.position.value,
        description=employee.description,
        agent_type=employee.agent_type.value if employee.agent_type else None,
        provider=employee.provider_config.get("provider") if employee.provider_config else None,
        model=employee.provider_config.get("model", employee.provider_config.get("model_id")) if employee.provider_config else None,
        status=employee.status.value,
        meta=metadata,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
    )


def model_to_employee(model: AIEmployeeModel) -> AIEmployee:
    """Convert AIEmployeeModel to AIEmployee dataclass"""
    from src.ai.agents import AgentType

    # Extract lifecycle timestamps from metadata
    metadata = model.meta or {}
    activated_at = None
    suspended_at = None
    retired_at = None

    if "activated_at" in metadata:
        from datetime import datetime

        activated_at = datetime.fromisoformat(metadata.pop("activated_at"))
    if "suspended_at" in metadata:
        from datetime import datetime

        suspended_at = datetime.fromisoformat(metadata.pop("suspended_at"))
    if "retired_at" in metadata:
        from datetime import datetime

        retired_at = datetime.fromisoformat(metadata.pop("retired_at"))

    # Extract statistical fields from metadata
    tasks_completed = metadata.pop("tasks_completed", 0)
    tasks_failed = metadata.pop("tasks_failed", 0)
    total_execution_time_seconds = metadata.pop("total_execution_time_seconds", 0.0)
    total_cost_usd = metadata.pop("total_cost_usd", 0.0)

    # Reconstruct provider_config from database columns
    provider_config = {}
    if model.provider:
        provider_config["provider"] = model.provider
    if model.model:
        provider_config["model"] = model.model
    return AIEmployee(
        id=UUID(model.id),
        name=model.name,
        department=Department(model.department),
        position=Position(model.position),
        description=model.description,
        agent_type=AgentType(model.agent_type) if model.agent_type else None,
        provider_config=provider_config,
        status=AIEmployeeStatus(model.status),
        activated_at=activated_at,
        suspended_at=suspended_at,
        retired_at=retired_at,
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
        total_execution_time_seconds=total_execution_time_seconds,
        total_cost_usd=total_cost_usd,
        metadata=metadata,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# ============================================================================
# Business Converters
# ============================================================================


def business_task_to_model(task: BusinessTask) -> BusinessTaskModel:
    """Convert BusinessTask dataclass to BusinessTaskModel"""
    return BusinessTaskModel(
        id=str(task.id),
        domain=task.domain.value,
        title=task.title,
        description=task.description,
        priority=task.priority.value,
        status=task.status.value,
        assigned_employee_id=str(task.assigned_employee_id) if task.assigned_employee_id else None,
        assigned_by=str(task.assigned_by) if task.assigned_by else None,
        assigned_at=task.assigned_at,
        owner_user_id=task.owner_user_id,
        created_by=task.created_by,
        context=task.context,
        tags=task.tags,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


def model_to_business_task(model: BusinessTaskModel) -> BusinessTask:
    """Convert BusinessTaskModel to BusinessTask dataclass"""
    return BusinessTask(
        id=UUID(model.id),
        domain=BusinessDomain(model.domain),
        title=model.title,
        description=model.description,
        priority=BusinessTaskPriority(model.priority),
        status=BusinessTaskStatus(model.status),
        assigned_employee_id=(
            UUID(model.assigned_employee_id) if model.assigned_employee_id else None
        ),
        assigned_by=UUID(model.assigned_by) if model.assigned_by else None,
        assigned_at=model.assigned_at,
        owner_user_id=model.owner_user_id,
        created_by=model.created_by,
        context=model.context or {},
        tags=model.tags or [],
        result=model.result,
        error=model.error,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
    )
