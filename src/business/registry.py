"""
Business Task Registry

Central registry for all business tasks (Single Source of Truth).
Similar to AIEmployeeRegistry, this provides a unified storage for business tasks.
"""

from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.models import (
    BusinessDomain,
    BusinessTask,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.core.errors import ResourceNotFoundError, ValidationError
from src.database.repositories.business import BusinessTaskRepository
from src.database.repositories.converters import business_task_to_model, model_to_business_task

logger = structlog.get_logger(__name__)


class BusinessTaskRegistry:
    """
    Registry for business tasks.

    Provides:
    - Task registration and lookup
    - Status tracking
    - Domain filtering
    - Priority management
    """

    def __init__(self, session: AsyncSession):
        """Initialize registry"""
        self.session = session
        self.repo = BusinessTaskRepository(session)
        logger.info("business_task_registry_initialized")

    async def register(self, task: BusinessTask) -> BusinessTask:
        """
        Register a business task.

        Args:
            task: Business task to register

        Returns:
            Registered task

        Raises:
            ValidationError: If task already exists
        """
        existing = await self.repo.get_by_id(str(task.id))
        if existing:
            raise ValidationError(f"Business task already exists: {task.id}")

        # Store in database
        model = business_task_to_model(task)
        saved_model = await self.repo.create(model)
        task = model_to_business_task(saved_model)

        logger.info(
            f"Business task registered: {task.title}",
            extra={
                "task_id": str(task.id),
                "domain": task.domain.value,
                "priority": task.priority.value,
            },
        )

        return task

    async def get(self, task_id: UUID) -> BusinessTask:
        """
        Get task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Business task

        Raises:
            ResourceNotFoundError: If task not found
        """
        model = await self.repo.get_by_id(str(task_id))
        if not model:
            raise ResourceNotFoundError(f"Business task not found: {task_id}")

        return model_to_business_task(model)

    async def update(self, task_id: UUID, task: BusinessTask) -> BusinessTask:
        """
        Update task.

        Args:
            task_id: Task UUID
            task: Updated task data

        Returns:
            Updated task

        Raises:
            ResourceNotFoundError: If task not found
        """
        model = await self.repo.get_by_id(str(task_id))
        if not model:
            raise ResourceNotFoundError(f"Business task not found: {task_id}")

        task.updated_at = datetime.now(UTC)

        # Update in database
        updated_model = business_task_to_model(task)
        # Convert model to dict for SQLAlchemy update
        update_dict = {
            "domain": updated_model.domain,
            "title": updated_model.title,
            "description": updated_model.description,
            "priority": updated_model.priority,
            "status": updated_model.status,
            "assigned_employee_id": updated_model.assigned_employee_id,
            "assigned_by": updated_model.assigned_by,
            "assigned_at": updated_model.assigned_at,
            "context": updated_model.context,
            "tags": updated_model.tags,
            "result": updated_model.result,
            "error": updated_model.error,
            "updated_at": updated_model.updated_at,
            "completed_at": updated_model.completed_at,
        }
        saved_model = await self.repo.update(str(task_id), update_dict)
        task = model_to_business_task(saved_model)

        logger.info(f"Business task updated: {task.title}", extra={"task_id": str(task_id)})

        return task

    async def delete(self, task_id: UUID) -> None:
        """
        Delete task.

        Args:
            task_id: Task UUID

        Raises:
            ResourceNotFoundError: If task not found
        """
        model = await self.repo.get_by_id(str(task_id))
        if not model:
            raise ResourceNotFoundError(f"Business task not found: {task_id}")

        task = model_to_business_task(model)
        await self.repo.delete(str(task_id))

        logger.info(f"Business task deleted: {task.title}", extra={"task_id": str(task_id)})

    async def list(
        self,
        domain: Optional[BusinessDomain] = None,
        status: Optional[BusinessTaskStatus] = None,
        priority: Optional[BusinessTaskPriority] = None,
        assigned_employee_id: Optional[UUID] = None,
    ) -> List[BusinessTask]:
        """
        List tasks with optional filters.

        Args:
            domain: Filter by domain
            status: Filter by status
            priority: Filter by priority
            assigned_employee_id: Filter by assigned employee

        Returns:
            List of matching tasks
        """
        # Get all tasks from database
        models = await self.repo.list_all()
        tasks = [model_to_business_task(m) for m in models]

        if domain:
            tasks = [t for t in tasks if t.domain == domain]

        if status:
            tasks = [t for t in tasks if t.status == status]

        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        if assigned_employee_id:
            tasks = [t for t in tasks if t.assigned_employee_id == assigned_employee_id]

        return tasks

    async def count_by_status(self, domain: Optional[BusinessDomain] = None) -> dict[str, int]:
        """
        Count tasks by status.

        Args:
            domain: Optional domain filter

        Returns:
            Dictionary of status counts
        """
        tasks = await self.list(domain=domain)
        counts = {status.value: 0 for status in BusinessTaskStatus}

        for task in tasks:
            counts[task.status.value] += 1

        return counts

    async def count_by_domain(self) -> dict[str, int]:
        """
        Count tasks by domain.

        Returns:
            Dictionary of domain counts
        """
        counts = {domain.value: 0 for domain in BusinessDomain}

        models = await self.repo.list_all()
        for model in models:
            task = model_to_business_task(model)
            counts[task.domain.value] += 1

        return counts

    async def get_employee_tasks(self, employee_id: UUID) -> List[BusinessTask]:
        """
        Get all tasks assigned to an employee.

        Args:
            employee_id: AI Employee UUID

        Returns:
            List of tasks
        """
        return await self.list(assigned_employee_id=employee_id)
