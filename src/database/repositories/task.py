"""
Task Repositories - Phase 2
Data access layer for Task and TaskResult
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TaskModel, TaskResultModel
from src.database.repository import BaseRepository


class TaskRepository(BaseRepository[TaskModel]):
    """Repository for Task operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskModel, session)

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        limit: int = 100,
    ) -> List[TaskModel]:
        """
        List tasks for a specific workflow

        Args:
            workflow_id: Workflow ID
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.workflow_id == str(workflow_id))
            .order_by(TaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaskModel]:
        """
        List tasks by status

        Args:
            status: Task status
            limit: Maximum tasks to return
            offset: Number to skip

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status == status)
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_pending(self, limit: int = 100) -> List[TaskModel]:
        """
        List pending tasks (PENDING or RUNNING), ordered by priority

        Args:
            limit: Maximum tasks to return

        Returns:
            List of tasks (high priority first)
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status.in_(["PENDING", "RUNNING"]))
            .order_by(TaskModel.priority.desc(), TaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_creator(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[TaskModel]:
        """
        List tasks by creator

        Args:
            user_id: Creator user ID
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.created_by == str(user_id))
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(
        self,
        task_type: str,
        limit: int = 100,
    ) -> List[TaskModel]:
        """
        List tasks by type

        Args:
            task_type: Task type
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.task_type == task_type)
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_subtasks(self, parent_task_id: UUID) -> List[TaskModel]:
        """
        List subtasks of a parent task

        Args:
            parent_task_id: Parent task ID

        Returns:
            List of subtasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.parent_task_id == str(parent_task_id))
            .order_by(TaskModel.created_at.asc())
        )
        return list(result.scalars().all())

    async def search_by_title(self, title_query: str, limit: int = 20) -> List[TaskModel]:
        """
        Search tasks by title (case-insensitive)

        Args:
            title_query: Title search query
            limit: Maximum tasks to return

        Returns:
            List of matching tasks
        """
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.title.ilike(f"%{title_query}%"))
            .order_by(TaskModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class TaskResultRepository(BaseRepository[TaskResultModel]):
    """Repository for TaskResult operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(TaskResultModel, session)

    async def list_by_task(
        self,
        task_id: UUID,
        limit: int = 100,
    ) -> List[TaskResultModel]:
        """
        List results for a specific task

        Args:
            task_id: Task ID
            limit: Maximum results to return

        Returns:
            List of results (newest first)
        """
        result = await self.session.execute(
            select(TaskResultModel)
            .where(TaskResultModel.task_id == str(task_id))
            .order_by(TaskResultModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_result(self, task_id: UUID) -> Optional[TaskResultModel]:
        """
        Get latest result for a task

        Args:
            task_id: Task ID

        Returns:
            Latest result if exists, None otherwise
        """
        result = await self.session.execute(
            select(TaskResultModel)
            .where(TaskResultModel.task_id == str(task_id))
            .order_by(TaskResultModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
