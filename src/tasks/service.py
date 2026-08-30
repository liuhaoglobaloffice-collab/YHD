"""
Task Service - Stage 5
Task lifecycle management
"""

from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import NotFoundError, ValidationError
from src.core.events import Event, EventBus
from src.database.repositories.converters import model_to_task, task_to_model
from src.database.repositories.task import TaskRepository
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.identity.rbac import Permission, require_permission
from src.tasks.models import (
    Task,
    TaskDependency,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskType,
)

logger = structlog.get_logger(__name__)


class TaskService:
    """
    Task Service - Task lifecycle management

    Manages task creation, updates, dependencies, and lifecycle.
    Enforces security and audit requirements.
    """

    def __init__(
        self,
        session: AsyncSession,
        audit_service: Optional[AuditService] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.session = session
        self.repo = TaskRepository(session)
        self.audit_service = audit_service or AuditService()
        self.event_bus = event_bus or EventBus()
        logger.info("task_service_initialized")

    async def create_task(
        self,
        title: str,
        description: str,
        task_type: TaskType,
        user: User,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assigned_to: Optional[List[UUID]] = None,
        workflow_id: Optional[UUID] = None,
        parent_task_id: Optional[UUID] = None,
        dependencies: Optional[List[TaskDependency]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        deadline: Optional[Any] = None,
        max_retries: int = 3,
    ) -> Task:
        """
        Create a new task

        Args:
            title: Task title
            description: Task description
            task_type: Type of task
            user: User creating the task
            priority: Task priority
            assigned_to: List of agent IDs to assign to
            workflow_id: Parent workflow ID
            parent_task_id: Parent task ID
            dependencies: Task dependencies
            input_data: Task input data
            metadata: Task metadata
            tags: Task tags
            deadline: Task deadline

        Returns:
            Created task

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Check permission
        require_permission(user, Permission.SYSTEM_WRITE)

        # Validate
        if not title or not title.strip():
            raise ValidationError("Task title is required")

        # Create task
        # creator_id must be UUID, convert from int user.id if needed
        creator_id: Union[UUID, None] = None
        if isinstance(user.id, int):
            # User.id is int - create a deterministic UUID from it
            creator_id = UUID(int=user.id)
        elif isinstance(user.id, UUID):
            creator_id = user.id
        elif isinstance(user.id, str):
            creator_id = UUID(user.id)

        task = Task(
            title=title.strip(),
            description=description.strip() if description else "",
            task_type=task_type,
            priority=priority,
            assigned_to=assigned_to or [],
            creator_id=creator_id,
            workflow_id=workflow_id,
            parent_task_id=parent_task_id,
            dependencies=dependencies or [],
            input_data=input_data or {},
            metadata=metadata or {},
            tags=tags or [],
            deadline=deadline,
            max_retries=max_retries,
        )

        # Store in database
        model = task_to_model(task)
        saved_model = await self.repo.create(model)
        task = model_to_task(saved_model)

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.CREATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={
                "title": task.title,
                "task_type": task.task_type.value,
                "priority": task.priority.value,
            },
            status="success",
        )

        # Event
        self.event_bus.publish(
            Event(
                name="task.created",
                data={
                    "task_id": str(task.id),
                    "title": task.title,
                    "task_type": task.task_type.value,
                    "creator_id": str(user.id),
                },
            )
        )

        logger.info(
            "task_created",
            task_id=task.id,
            title=task.title,
            task_type=task.task_type.value,
            user_id=user.id,
        )

        return task

    async def create_task_from_assessment(self, assessment: Dict[str, Any], actor: Optional[Any] = None) -> Task:
        """
        Create a task from a normalized supplier risk assessment dict.

        This method intentionally bypasses the external permission checks required by
        create_task (which expects an authenticated User) so that internal automation
        (e.g., risk pipeline) can create tasks. It still records an audit log; user_id
        will be None when actor is not provided.
        """
        # Validate minimal contract
        assessment_id = assessment.get("assessment_id")
        if not assessment_id:
            raise ValueError("assessment_id is required to create a task from assessment")

        # Build payload
        from src.business.supplier.task_adapter import build_task_payload_from_assessment

        payload = build_task_payload_from_assessment(
            assessment, created_by=(getattr(actor, "username", "system") if actor else "system")
        )

        # Map priority tokens (P0/P1/P2) to TaskPriority
        priority_map = {
            "P0": TaskPriority.CRITICAL,
            "P1": TaskPriority.HIGH,
            "P2": TaskPriority.MEDIUM,
        }
        priority_token = payload.get("priority", "P1")
        priority = priority_map.get(priority_token, TaskPriority.MEDIUM)

        # Map task_type string to TaskType if possible
        task_type_str = payload.get("task_type", "other")
        try:
            task_type = TaskType(task_type_str)
        except ValueError:
            task_type = TaskType.OTHER

        title = payload.get("title", "Task from assessment")
        description = payload.get("description", "")

        # metadata must include assessment_reference
        metadata = payload.get("reference", {})
        # Wrap under explicit key to follow other code expectations
        metadata_wrapped = {"assessment_reference": metadata}

        # Creator id if actor provided and has id attribute; otherwise use a deterministic
        # placeholder UUID so the underlying TaskModel constraint is satisfied.
        creator_id = getattr(actor, "id", None) if actor else None
        if creator_id is None:
            creator_id = UUID("00000000-0000-0000-0000-000000000000")

        # Construct Task dataclass and persist via repository
        task = Task(
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            assigned_to=[],
            creator_id=creator_id,
            metadata=metadata_wrapped,
            tags=[],
        )

        model = task_to_model(task)
        saved_model = await self.repo.create(model)
        created_task = model_to_task(saved_model)

        # Audit - log as TASK_CREATED (fallback to CREATE if TASK_CREATED not present)
        action = getattr(AuditAction, 'TASK_CREATED', AuditAction.CREATE)
        await self.audit_service.log(
            self.session,
            action=action,
            resource_type="task",
            status="success",
            user_id=creator_id,
            resource_id=str(created_task.id),
            details={"title": created_task.title, "reference": metadata},
        )

        # Publish event
        self.event_bus.publish(
            Event(
                name="task.created",
                data={"task_id": str(created_task.id), "title": created_task.title},
            )
        )

        logger.info("task_created_from_assessment", task_id=created_task.id, assessment_id=assessment_id)

        return created_task

    async def get_task(self, task_id: UUID, user: User) -> Task:
        """
        Get task by ID

        Args:
            task_id: Task ID
            user: User requesting the task

        Returns:
            Task

        Raises:
            NotFoundError: If task not found
            PermissionDeniedError: If user lacks permission
        """
        require_permission(user, Permission.SYSTEM_READ)

        model = await self.repo.get_by_id(str(task_id))
        task = model_to_task(model) if model else None
        if not task:
            raise NotFoundError(f"Task not found: {task_id}")

        return task

    async def list_tasks(
        self,
        user: User,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        priority: Optional[TaskPriority] = None,
        workflow_id: Optional[UUID] = None,
        assigned_to: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[Task]:
        """
        List tasks with filters

        Args:
            user: User requesting tasks
            status: Filter by status
            task_type: Filter by type
            priority: Filter by priority
            workflow_id: Filter by workflow
            assigned_to: Filter by assignee
            limit: Max results

        Returns:
            List of tasks
        """
        require_permission(user, Permission.SYSTEM_READ)

        # Get all tasks from database
        models = await self.repo.list_all()
        tasks = [model_to_task(m) for m in models]

        # Apply filters
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        if workflow_id:
            tasks = [t for t in tasks if t.workflow_id == workflow_id]
        if assigned_to:
            tasks = [t for t in tasks if assigned_to in t.assigned_to]

        # Sort by priority and created_at
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4,
        }
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))

        return tasks[:limit]

    async def update_task_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        user: User,
        result: Optional[TaskResult] = None,
    ) -> Task:
        """
        Update task status

        Args:
            task_id: Task ID
            status: New status
            user: User updating status
            result: Task result (for completed/failed)

        Returns:
            Updated task
        """
        require_permission(user, Permission.SYSTEM_WRITE)

        task = await self.get_task(task_id, user)
        old_status = task.status

        # Update status
        if status == TaskStatus.RUNNING:
            task.mark_running()
        elif status == TaskStatus.COMPLETED:
            if not result:
                result = TaskResult(success=True)
            task.mark_completed(result)
        elif status == TaskStatus.FAILED:
            if not result:
                result = TaskResult(success=False, error="Task failed")
            task.mark_failed(result.error or "Unknown error")
        elif status == TaskStatus.CANCELLED:
            task.mark_cancelled()
        elif status == TaskStatus.BLOCKED:
            task.mark_blocked()
        else:
            task.status = status

        # Update in database
        model = task_to_model(task)
        # Convert model to dict (exclude SQLAlchemy internal attrs)
        model_dict = {k: v for k, v in vars(model).items() if not k.startswith("_")}
        await self.repo.update(str(task_id), model_dict)

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={
                "old_status": old_status.value,
                "new_status": status.value,
            },
            status="success",
        )

        # Event
        self.event_bus.publish(
            Event(
                name=f"task.{status.value}",
                data={
                    "task_id": str(task.id),
                    "title": task.title,
                    "old_status": old_status.value,
                    "new_status": status.value,
                },
            )
        )

        logger.info(
            "task_status_updated",
            task_id=task.id,
            old_status=old_status.value,
            new_status=status.value,
        )

        return task

    async def assign_task(
        self,
        task_id: UUID,
        agent_ids: List[UUID],
        user: User,
    ) -> Task:
        """
        Assign task to agents

        Args:
            task_id: Task ID
            agent_ids: List of agent IDs
            user: User assigning task

        Returns:
            Updated task
        """
        require_permission(user, Permission.SYSTEM_WRITE)

        task = await self.get_task(task_id, user)
        old_assigned = task.assigned_to.copy()
        task.assigned_to = agent_ids

        # Update in database
        model = task_to_model(task)
        # Convert model to dict (exclude SQLAlchemy internal attrs)
        model_dict = {k: v for k, v in vars(model).items() if not k.startswith("_")}
        await self.repo.update(str(task_id), model_dict)

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={
                "old_assigned": [str(a) for a in old_assigned],
                "new_assigned": [str(a) for a in agent_ids],
            },
            status="success",
        )

        logger.info(
            "task_assigned",
            task_id=task.id,
            agent_ids=[str(a) for a in agent_ids],
        )

        return task

    async def delete_task(self, task_id: UUID, user: User) -> bool:
        """
        Delete task

        Args:
            task_id: Task ID
            user: User deleting task

        Returns:
            True if deleted
        """
        require_permission(user, Permission.SYSTEM_ADMIN)

        task = await self.get_task(task_id, user)

        # Cannot delete running tasks
        if task.status == TaskStatus.RUNNING:
            raise ValidationError("Cannot delete running task")

        await self.repo.delete(str(task_id))

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.DELETE,
            resource_type="task",
            resource_id=task_id,
            user_id=user.id,
            details={"title": task.title},
            status="success",
        )

        logger.info("task_deleted", task_id=task_id, user_id=user.id)

        return True

    async def get_ready_tasks(self, user: User) -> List[Task]:
        """
        Get tasks ready for execution

        Args:
            user: User requesting tasks

        Returns:
            List of ready tasks
        """
        require_permission(user, Permission.SYSTEM_READ)

        # Get all tasks from database
        models = await self.repo.list_all()
        all_tasks = [model_to_task(m) for m in models]

        # Get completed task IDs
        completed_tasks: Set[UUID] = {t.id for t in all_tasks if t.status == TaskStatus.COMPLETED}

        # Find ready tasks
        ready_tasks = [task for task in all_tasks if task.is_ready(completed_tasks)]

        # Sort by priority
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.MEDIUM: 3,
            TaskPriority.LOW: 4,
        }
        ready_tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))

        return ready_tasks

    async def get_task_dependencies(self, task_id: UUID, user: User) -> List[Task]:
        """
        Get task dependencies

        Args:
            task_id: Task ID
            user: User requesting dependencies

        Returns:
            List of dependency tasks
        """
        require_permission(user, Permission.SYSTEM_READ)

        task = await self.get_task(task_id, user)

        dependency_tasks = []
        for dep in task.dependencies:
            model = await self.repo.get_by_id(str(dep.task_id))
            dep_task = model_to_task(model) if model else None
            if dep_task:
                dependency_tasks.append(dep_task)

        return dependency_tasks

    async def complete_task(
        self,
        task_id: UUID,
        result: Dict[str, Any],
        user: User,
    ) -> Task:
        """
        Complete a task with result

        Args:
            task_id: Task ID
            result: Task result data
            user: User completing task

        Returns:
            Updated task
        """
        task = await self.get_task(task_id, user)
        task.status = TaskStatus.COMPLETED
        from .models import TaskResult

        task.result = TaskResult(success=True, output=result)

        # Update in database
        model = task_to_model(task)
        # Convert model to dict (exclude SQLAlchemy internal attrs)
        model_dict = {k: v for k, v in vars(model).items() if not k.startswith("_")}
        await self.repo.update(str(task_id), model_dict)

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={
                "action": "complete",
                "result": result,
            },
            status="success",
        )

        # Event
        self.event_bus.publish(
            Event(
                name="task.completed",
                data={
                    "task_id": str(task.id),
                    "title": task.title,
                },
            )
        )

        logger.info(
            "task_completed",
            task_id=task.id,
            title=task.title,
            user_id=user.id,
        )

        return task

    async def fail_task(
        self,
        task_id: UUID,
        error: str,
        user: User,
    ) -> Task:
        """
        Fail a task with error

        Args:
            task_id: Task ID
            error: Error message
            user: User failing task

        Returns:
            Updated task
        """
        task = await self.get_task(task_id, user)
        task.status = TaskStatus.FAILED
        task.error = error

        # Update in database
        model = task_to_model(task)
        # Convert model to dict (exclude SQLAlchemy internal attrs)
        model_dict = {k: v for k, v in vars(model).items() if not k.startswith("_")}
        await self.repo.update(str(task_id), model_dict)

        # Audit
        await self.audit_service.log(
            self.session,
            action=AuditAction.UPDATE,
            resource_type="task",
            resource_id=task.id,
            user_id=user.id,
            details={
                "action": "fail",
                "error": error,
            },
            status="failure",
        )

        # Event
        self.event_bus.publish(
            Event(
                name="task.failed",
                data={
                    "task_id": str(task.id),
                    "title": task.title,
                    "error": error,
                },
            )
        )

        logger.info(
            "task_failed",
            task_id=task.id,
            title=task.title,
            error=error,
            user_id=user.id,
        )

        return task
