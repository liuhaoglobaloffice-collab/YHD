"""
Business Repositories - Phase 2
Data access layer for Business Tasks
"""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import BusinessTaskModel
from src.database.repository import BaseRepository


class BusinessTaskRepository(BaseRepository[BusinessTaskModel]):
    """Repository for BusinessTask operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(BusinessTaskModel, session)

    async def list_by_domain(
        self,
        domain: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BusinessTaskModel]:
        """
        List tasks by business domain

        Args:
            domain: Business domain
            limit: Maximum tasks to return
            offset: Number to skip

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.domain == domain)
            .order_by(BusinessTaskModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_employee(
        self,
        employee_id: UUID,
        limit: int = 100,
    ) -> List[BusinessTaskModel]:
        """
        List tasks assigned to an employee

        Args:
            employee_id: Employee ID
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.assigned_employee_id == str(employee_id))
            .order_by(BusinessTaskModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[BusinessTaskModel]:
        """
        List tasks by status

        Args:
            status: Task status
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.status == status)
            .order_by(BusinessTaskModel.priority.desc(), BusinessTaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        limit: int = 100,
    ) -> List[BusinessTaskModel]:
        """
        List tasks for a specific workflow

        Args:
            workflow_id: Workflow ID
            limit: Maximum tasks to return

        Returns:
            List of tasks
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.workflow_id == str(workflow_id))
            .order_by(BusinessTaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_pending(self, limit: int = 100) -> List[BusinessTaskModel]:
        """
        List pending business tasks

        Args:
            limit: Maximum tasks to return

        Returns:
            List of pending tasks (high priority first)
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.status.in_(["CREATED", "IN_PROGRESS"]))
            .order_by(BusinessTaskModel.priority.desc(), BusinessTaskModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_title(self, title_query: str, limit: int = 20) -> List[BusinessTaskModel]:
        """
        Search tasks by title (case-insensitive)

        Args:
            title_query: Title search query
            limit: Maximum tasks to return

        Returns:
            List of matching tasks
        """
        result = await self.session.execute(
            select(BusinessTaskModel)
            .where(BusinessTaskModel.title.ilike(f"%{title_query}%"))
            .order_by(BusinessTaskModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
