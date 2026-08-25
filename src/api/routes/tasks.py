"""
Tasks API Routes - Phase 2F-2.5 Service Factory Integration

Endpoints:
- POST /api/v1/tasks - Create task
- GET /api/v1/tasks - List tasks
- GET /api/v1/tasks/{task_id} - Get task
- PUT /api/v1/tasks/{task_id}/status - Update status
- PUT /api/v1/tasks/{task_id}/assign - Assign agents
- DELETE /api/v1/tasks/{task_id} - Delete task
- POST /api/v1/tasks/{task_id}/complete - Complete task
- GET /api/v1/tasks/ready - Get ready tasks

Architecture (Phase 2F-2.5):
    API Endpoint
        ↓ (Factory Dependency)
    TaskService (fully initialized)
        ↓
    TaskRepository
        ↓
    Database
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...api.dependencies.approval import require_approval_for
from ...api.dependencies.database import get_db
from ...api.dependencies.permissions import require_permission
from ...api.factories import get_task_service
from ...identity.audit import AuditAction, AuditService
from ...identity.models import User
from ...tasks.models import TaskPriority, TaskStatus, TaskType
from ...tasks.service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


# Request/Response Models
class CreateTaskRequest(BaseModel):
    """Create task request."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_agents: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class UpdateTaskStatusRequest(BaseModel):
    """Update task status request."""

    status: TaskStatus
    result: Optional[dict] = None


class AssignTaskRequest(BaseModel):
    """Assign task request."""

    agent_ids: List[str] = Field(..., min_items=1)


class CompleteTaskRequest(BaseModel):
    """Complete task request."""

    result: dict = Field(default_factory=dict)


class TaskResponse(BaseModel):
    """Task response."""

    task_id: str
    title: str
    description: str
    task_type: str
    status: str
    priority: str
    assigned_agents: List[str]
    created_by: str
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    dependencies: List[dict]
    result: Optional[dict]
    metadata: dict

    @classmethod
    def from_task(cls, task):
        """Convert Task to response."""
        return cls(
            task_id=str(task.task_id),
            title=task.title,
            description=task.description,
            task_type=task.task_type.value,
            status=task.status.value,
            priority=task.priority.value,
            assigned_agents=task.assigned_agents,
            created_by=str(task.created_by),
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            dependencies=[
                {
                    "task_id": str(dep.task_id),
                    "type": dep.dependency_type,
                }
                for dep in task.dependencies
            ],
            result=task.result.to_dict() if task.result else None,
            metadata=task.metadata,
        )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    request: CreateTaskRequest,
    task_service: TaskService = Depends(get_task_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "create")),
):
    """
    Create new task.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        task = await task_service.create_task(
            title=request.title,
            description=request.description,
            task_type=request.task_type,
            priority=request.priority,
            assigned_agents=request.assigned_agents,
            dependencies=request.dependencies,
            metadata=request.metadata,
            user=current_user,
        )

        # Audit: Task created
        await AuditService.log(
            session=session,
            action=AuditAction.TASK_CREATED,
            resource_type="task",
            resource_id=str(task.task_id),
            status="success",
            user_id=current_user.id,
            details={
                "title": request.title,
                "task_type": request.task_type.value,
                "priority": request.priority.value,
            },
        )

        return TaskResponse.from_task(task)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None),
    task_type: Optional[TaskType] = Query(None),
    priority: Optional[TaskPriority] = Query(None),
    assigned_agent: Optional[str] = Query(None),
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "read")),
):
    """
    List tasks with optional filters.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        tasks = await task_service.list_tasks(
            user=current_user,
            status=status,
            task_type=task_type,
            priority=priority,
            assigned_to=UUID(assigned_agent) if assigned_agent else None,
        )

        return [TaskResponse.from_task(task) for task in tasks]

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ready", response_model=List[TaskResponse])
async def get_ready_tasks(
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "read")),
):
    """
    Get ready-to-execute tasks.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        tasks = await task_service.get_ready_tasks(user=current_user)

        return [TaskResponse.from_task(task) for task in tasks]

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "read")),
):
    """
    Get task by ID.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        task = await task_service.get_task(task_id, current_user)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return TaskResponse.from_task(task)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: UUID,
    request: UpdateTaskStatusRequest,
    task_service: TaskService = Depends(get_task_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "update")),
):
    """
    Update task status.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        task = await task_service.update_task_status(
            task_id=task_id,
            status=request.status,
            result=request.result,
            user=current_user,
        )

        return TaskResponse.from_task(task)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{task_id}/assign", response_model=TaskResponse)
async def assign_task(
    task_id: UUID,
    request: AssignTaskRequest,
    task_service: TaskService = Depends(get_task_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "assign")),
):
    """
    Assign task to agents.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        task = await task_service.assign_task(
            task_id=task_id,
            agent_ids=request.agent_ids,
            user=current_user,
        )

        # Audit: Task assigned
        await AuditService.log(
            session=session,
            action=AuditAction.TASK_ASSIGNED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=current_user.id,
            details={"agent_ids": request.agent_ids},
        )

        return TaskResponse.from_task(task)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: UUID,
    request: CompleteTaskRequest,
    task_service: TaskService = Depends(get_task_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "complete")),
):
    """
    Complete task.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    try:
        task = await task_service.complete_task(
            task_id=task_id,
            result=request.result,
            user=current_user,
        )

        # Audit: Task completed
        await AuditService.log(
            session=session,
            action=AuditAction.TASK_COMPLETED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=current_user.id,
            details={"action": "complete"},
        )

        return TaskResponse.from_task(task)

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("task", "delete")),
    _approval: None = Depends(require_approval_for("task", "delete")),
):
    """
    Delete task (requires approval for high-risk operations).

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Phase 2 Governance: Approval required for delete operations.
    """
    try:
        deleted = await task_service.delete_task(task_id, current_user)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        # Audit: Task deleted
        await AuditService.log(
            session=session,
            action=AuditAction.TASK_DELETED,
            resource_type="task",
            resource_id=str(task_id),
            status="success",
            user_id=current_user.id,
            details={"action": "delete"},
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
