"""
Workflow Repositories - Phase 2
Data access layer for Workflow and WorkflowExecution
"""

from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import WorkflowExecutionModel, WorkflowModel
from src.database.repository import BaseRepository


class WorkflowRepository(BaseRepository[WorkflowModel]):
    """Repository for Workflow operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(WorkflowModel, session)

    async def list_by_creator(self, user_id: UUID, limit: int = 100) -> List[WorkflowModel]:
        """
        List workflows by creator

        Args:
            user_id: Creator user ID
            limit: Maximum workflows to return

        Returns:
            List of workflows
        """
        result = await self.session.execute(
            select(WorkflowModel)
            .where(WorkflowModel.created_by == str(user_id))
            .order_by(WorkflowModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_enabled(self, limit: int = 100) -> List[WorkflowModel]:
        """
        List enabled workflows

        Args:
            limit: Maximum workflows to return

        Returns:
            List of enabled workflows
        """
        result = await self.session.execute(
            select(WorkflowModel)
            .where(WorkflowModel.enabled)
            .order_by(WorkflowModel.name)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_by_name(self, name_query: str, limit: int = 20) -> List[WorkflowModel]:
        """
        Search workflows by name (case-insensitive)

        Args:
            name_query: Name search query
            limit: Maximum workflows to return

        Returns:
            List of matching workflows
        """
        result = await self.session.execute(
            select(WorkflowModel)
            .where(WorkflowModel.name.ilike(f"%{name_query}%"))
            .order_by(WorkflowModel.name)
            .limit(limit)
        )
        return list(result.scalars().all())


class WorkflowExecutionRepository(BaseRepository[WorkflowExecutionModel]):
    """Repository for WorkflowExecution operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(WorkflowExecutionModel, session)

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkflowExecutionModel]:
        """
        List executions for a specific workflow

        Args:
            workflow_id: Workflow ID
            limit: Maximum executions to return
            offset: Number to skip

        Returns:
            List of executions (newest first)
        """
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.workflow_id == str(workflow_id))
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[WorkflowExecutionModel]:
        """
        List executions by status

        Args:
            status: Execution status
            limit: Maximum executions to return

        Returns:
            List of executions
        """
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.status == status)
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 100,
    ) -> List[WorkflowExecutionModel]:
        """
        List executions by user

        Args:
            user_id: User ID
            limit: Maximum executions to return

        Returns:
            List of executions
        """
        result = await self.session.execute(
            select(WorkflowExecutionModel)
            .where(WorkflowExecutionModel.user_id == str(user_id))
            .order_by(WorkflowExecutionModel.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
