"""
Business Service

Orchestrates business operations by integrating:
- AI Employees (Stage 6)
- Workflows (Stage 5)
- Tasks (Stage 5)
- RBAC (Stage 2)
- Audit (Stage 2)
"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.business.models import (
    BusinessDomain,
    BusinessMetrics,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.business.registry import BusinessTaskRegistry
from src.core.errors import PermissionDeniedError, ValidationError
from src.identity.audit import AuditAction, AuditService
from src.identity.rbac import Permission, RBACService
from src.workforce.models import AIEmployeeStatus
from src.workforce.registry import AIEmployeeRegistry

logger = structlog.get_logger(__name__)


class BusinessService:
    """
    Business service orchestrates business operations.

    Integrates:
    - Business Task Registry (Single Source of Truth for business tasks)
    - AI Employee Registry (Stage 6)
    - RBAC (Stage 2)
    - Audit (Stage 2)

    Future integration points (not in Stage 7):
    - Workflow execution
    - Task execution
    - Knowledge retrieval
    """

    def __init__(
        self,
        task_registry: BusinessTaskRegistry,
        employee_registry: AIEmployeeRegistry,
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        """Initialize business service"""
        self.task_registry = task_registry
        self.employee_registry = employee_registry
        self.rbac = rbac_service
        self.audit = audit_service
        logger.info("business_service_initialized")

    async def create_task(
        self,
        user_id: UUID,
        domain: BusinessDomain,
        title: str,
        description: str,
        priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> BusinessTask:
        """
        Create a business task.

        Args:
            user_id: User creating the task
            domain: Business domain
            title: Task title
            description: Task description
            priority: Task priority
            context: Optional context data
            tags: Optional tags

        Returns:
            Created business task

        Raises:
            PermissionDeniedError: If user lacks permission
            ValidationError: If validation fails
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_CREATE):
            raise PermissionDeniedError("User lacks TASK_CREATE permission")

        # Validate
        if not title:
            raise ValidationError("Task title is required")

        if not description:
            raise ValidationError("Task description is required")

        # Create task
        task = BusinessTask(
            domain=domain,
            title=title,
            description=description,
            priority=priority,
            status=BusinessTaskStatus.CREATED,
            context=context or {},
            tags=tags or [],
        )

        # Register
        task = await self.task_registry.register(task)

        # Audit
        await self.audit.log(
            self.rbac.session,
            action=AuditAction.TASK_CREATED,
            user_id=user_id,
            resource_type="business_task",
            resource_id=str(task.id),
            status="success",
            details={
                "domain": domain.value,
                "title": title,
                "priority": priority.value,
            },
        )

        logger.info(
            f"Business task created: {title}",
            extra={
                "task_id": str(task.id),
                "domain": domain.value,
                "user_id": str(user_id),
            },
        )

        return task

    async def assign_task(
        self,
        user_id: UUID,
        task_id: UUID,
        employee_id: UUID,
    ) -> BusinessTask:
        """
        Assign task to AI employee.

        Args:
            user_id: User assigning the task
            task_id: Task UUID
            employee_id: AI Employee UUID

        Returns:
            Updated task

        Raises:
            PermissionDeniedError: If user lacks permission
            ValidationError: If assignment invalid
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_ASSIGN):
            raise PermissionDeniedError("User lacks TASK_ASSIGN permission")

        # Get task
        task = await self.task_registry.get(task_id)

        # Get employee
        employee = await self.employee_registry.get(employee_id)

        # Validate employee status
        if employee.status != AIEmployeeStatus.ACTIVE:
            raise ValidationError(
                f"Cannot assign task to employee in status: {employee.status.value}"
            )

        # Validate task status
        if task.status not in [BusinessTaskStatus.CREATED, BusinessTaskStatus.ASSIGNED]:
            raise ValidationError(f"Cannot assign task in status: {task.status.value}")

        # Update task
        task.assigned_employee_id = employee_id
        task.assigned_by = user_id
        task.assigned_at = datetime.now(UTC)
        task.status = BusinessTaskStatus.ASSIGNED
        task.updated_at = datetime.now(UTC)

        # Update registry
        task = await self.task_registry.update(task_id, task)

        # Audit
        await self.audit.log(
            self.rbac.session,
            action=AuditAction.TASK_ASSIGNED,
            user_id=user_id,
            resource_type="business_task",
            resource_id=str(task_id),
            status="success",
            details={
                "employee_id": str(employee_id),
                "employee_name": employee.name,
            },
        )

        logger.info(
            f"Task assigned: {task.title} -> {employee.name}",
            extra={
                "task_id": str(task_id),
                "employee_id": str(employee_id),
                "user_id": str(user_id),
            },
        )

        return task

    async def start_task(
        self,
        user_id: UUID,
        task_id: UUID,
    ) -> BusinessTask:
        """
        Start task execution.

        Args:
            user_id: User starting the task
            task_id: Task UUID

        Returns:
            Updated task

        Raises:
            PermissionDeniedError: If user lacks permission
            ValidationError: If task cannot be started
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_EXECUTE):
            raise PermissionDeniedError("User lacks TASK_EXECUTE permission")

        # Get task
        task = await self.task_registry.get(task_id)

        # Validate status
        if task.status != BusinessTaskStatus.ASSIGNED:
            raise ValidationError(f"Cannot start task in status: {task.status.value}")

        # Validate assignment
        if not task.assigned_employee_id:
            raise ValidationError("Task must be assigned before starting")

        # Update task
        task.status = BusinessTaskStatus.IN_PROGRESS
        task.updated_at = datetime.now(UTC)

        # Update registry
        task = await self.task_registry.update(task_id, task)

        # Audit
        await self.audit.log(
            self.rbac.session,
            action=AuditAction.TASK_STARTED,
            user_id=user_id,
            resource_type="business_task",
            resource_id=str(task_id),
            status="success",
            details={"title": task.title},
        )

        logger.info(
            f"Task started: {task.title}", extra={"task_id": str(task_id), "user_id": str(user_id)}
        )

        return task

    async def complete_task(
        self,
        user_id: UUID,
        task_id: UUID,
        result: Optional[Dict[str, Any]] = None,
    ) -> BusinessTask:
        """
        Complete task.

        Args:
            user_id: User completing the task
            task_id: Task UUID
            result: Optional result data

        Returns:
            Updated task

        Raises:
            PermissionDeniedError: If user lacks permission
            ValidationError: If task cannot be completed
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_UPDATE):
            raise PermissionDeniedError("User lacks TASK_COMPLETE permission")

        # Get task
        task = await self.task_registry.get(task_id)

        # Validate status
        if task.status not in [BusinessTaskStatus.IN_PROGRESS, BusinessTaskStatus.REVIEW]:
            raise ValidationError(f"Cannot complete task in status: {task.status.value}")

        # Update task
        task.status = BusinessTaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        # Update registry
        task = await self.task_registry.update(task_id, task)

        # Audit
        await self.audit.log(
            self.rbac.session,
            action=AuditAction.TASK_COMPLETED,
            user_id=user_id,
            resource_type="business_task",
            resource_id=str(task_id),
            status="success",
            details={"title": task.title},
        )

        logger.info(
            f"Task completed: {task.title}",
            extra={"task_id": str(task_id), "user_id": str(user_id)},
        )

        return task

    async def fail_task(
        self,
        user_id: UUID,
        task_id: UUID,
        error: str,
    ) -> BusinessTask:
        """
        Mark task as failed.

        Args:
            user_id: User failing the task
            task_id: Task UUID
            error: Error message

        Returns:
            Updated task

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_UPDATE):
            raise PermissionDeniedError("User lacks TASK_COMPLETE permission")

        # Get task
        task = await self.task_registry.get(task_id)

        # Update task
        task.status = BusinessTaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.now(UTC)
        task.updated_at = datetime.now(UTC)

        # Update registry
        task = await self.task_registry.update(task_id, task)

        # Audit
        await self.audit.log(
            self.rbac.session,
            action=AuditAction.TASK_FAILED,
            user_id=user_id,
            resource_type="business_task",
            resource_id=str(task_id),
            success=False,
            details={"title": task.title, "error": error},
        )

        logger.error(f"Task failed: {task.title}", extra={"task_id": str(task_id), "error": error})

        return task

    async def get_task(self, user_id: UUID, task_id: UUID) -> BusinessTask:
        """
        Get task by ID.

        Args:
            user_id: User requesting task
            task_id: Task UUID

        Returns:
            Business task

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_READ):
            raise PermissionDeniedError("User lacks TASK_READ permission")

        return await self.task_registry.get(task_id)

    async def list_tasks(
        self,
        user_id: UUID,
        domain: Optional[BusinessDomain] = None,
        status: Optional[BusinessTaskStatus] = None,
        priority: Optional[BusinessTaskPriority] = None,
        assigned_employee_id: Optional[UUID] = None,
    ) -> List[BusinessTask]:
        """
        List tasks with filters.

        Args:
            user_id: User requesting tasks
            domain: Filter by domain
            status: Filter by status
            priority: Filter by priority
            assigned_employee_id: Filter by assigned employee

        Returns:
            List of tasks

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.TASK_READ):
            raise PermissionDeniedError("User lacks TASK_READ permission")

        return await self.task_registry.list(
            domain=domain,
            status=status,
            priority=priority,
            assigned_employee_id=assigned_employee_id,
        )

    async def get_domain_metrics(
        self,
        user_id: UUID,
        domain: BusinessDomain,
    ) -> BusinessMetrics:
        """
        Get metrics for a business domain.

        Args:
            user_id: User requesting metrics
            domain: Business domain

        Returns:
            Business metrics

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user_id, Permission.SYSTEM_READ):
            raise PermissionDeniedError("User lacks SYSTEM_READ permission")

        tasks = await self.task_registry.list(domain=domain)

        total = len(tasks)
        completed = len([t for t in tasks if t.status == BusinessTaskStatus.COMPLETED])
        failed = len([t for t in tasks if t.status == BusinessTaskStatus.FAILED])
        in_progress = len([t for t in tasks if t.status == BusinessTaskStatus.IN_PROGRESS])

        # Calculate avg completion time
        completed_tasks_with_time = [
            t for t in tasks if t.status == BusinessTaskStatus.COMPLETED and t.completed_at
        ]

        avg_time = 0.0
        if completed_tasks_with_time:
            total_seconds = sum(
                (t.completed_at - t.created_at).total_seconds() for t in completed_tasks_with_time
            )
            avg_time = total_seconds / len(completed_tasks_with_time)

        # Calculate success rate
        success_rate = 0.0
        if completed + failed > 0:
            success_rate = completed / (completed + failed)

        return BusinessMetrics(
            domain=domain,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            in_progress_tasks=in_progress,
            avg_completion_time_seconds=avg_time,
            success_rate=success_rate,
        )
