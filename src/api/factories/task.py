"""
Task Service Factory

Phase 2F-2.5: Dependency injection factory for TaskService.

Handles:
- AsyncSession injection
- AuditService integration (optional)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_employee_service, get_db
from src.api.dependencies.database import get_db
from src.tasks.executor import TaskExecutor
from src.tasks.service import TaskService


async def get_task_service(
    session: AsyncSession = Depends(get_db),
) -> TaskService:
    """
    Create TaskService with dependencies.

    Phase 2F-2.5: Service Factory Pattern

    Dependencies injected:
    - AsyncSession (for repository access)
    - AuditService (optional)

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured TaskService instance
    """
    return TaskService(
        session=session,
        audit_service=None,  # Optional audit service
    )


async def get_task_executor(
    task_service: TaskService = Depends(get_task_service),
    employee_service = Depends(get_employee_service),
) -> TaskExecutor:
    """
    Create TaskExecutor with dependencies.

    Dependencies:
    - TaskService (for task state management)
    - AIEmployeeService (for AI task execution delegation)

    Returns:
        Fully configured TaskExecutor instance
    """
    return TaskExecutor(
        task_service=task_service,
        employee_service=employee_service,
    )
