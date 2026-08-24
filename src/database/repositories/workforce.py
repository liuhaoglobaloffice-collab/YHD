"""
Workforce Repositories - Phase 2
Data access layer for AI Employees, Performance, and Cost tracking
"""

from datetime import UTC, datetime, timedelta
from typing import List
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    AIEmployeeModel,
    EmployeeCostModel,
    EmployeePerformanceModel,
)
from src.database.repository import BaseRepository


class AIEmployeeRepository(BaseRepository[AIEmployeeModel]):
    """Repository for AIEmployee operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(AIEmployeeModel, session)

    async def list_by_department(self, department: str) -> List[AIEmployeeModel]:
        """
        List employees by department

        Args:
            department: Department name

        Returns:
            List of employees
        """
        result = await self.session.execute(
            select(AIEmployeeModel)
            .where(AIEmployeeModel.department == department)
            .order_by(AIEmployeeModel.name)
        )
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> List[AIEmployeeModel]:
        """
        List employees by status

        Args:
            status: Employee status

        Returns:
            List of employees
        """
        result = await self.session.execute(
            select(AIEmployeeModel)
            .where(AIEmployeeModel.status == status)
            .order_by(AIEmployeeModel.department, AIEmployeeModel.name)
        )
        return list(result.scalars().all())

    async def list_active(self) -> List[AIEmployeeModel]:
        """
        List active employees

        Returns:
            List of active employees
        """
        return await self.list_by_status("ACTIVE")

    async def list_by_position(self, position: str) -> List[AIEmployeeModel]:
        """
        List employees by position

        Args:
            position: Position name

        Returns:
            List of employees
        """
        result = await self.session.execute(
            select(AIEmployeeModel)
            .where(AIEmployeeModel.position == position)
            .order_by(AIEmployeeModel.name)
        )
        return list(result.scalars().all())

    async def search_by_name(self, name_query: str, limit: int = 20) -> List[AIEmployeeModel]:
        """
        Search employees by name (case-insensitive)

        Args:
            name_query: Name search query
            limit: Maximum employees to return

        Returns:
            List of matching employees
        """
        result = await self.session.execute(
            select(AIEmployeeModel)
            .where(AIEmployeeModel.name.ilike(f"%{name_query}%"))
            .order_by(AIEmployeeModel.name)
            .limit(limit)
        )
        return list(result.scalars().all())


class EmployeePerformanceRepository(BaseRepository[EmployeePerformanceModel]):
    """Repository for EmployeePerformance operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(EmployeePerformanceModel, session)

    async def list_by_employee(
        self,
        employee_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EmployeePerformanceModel]:
        """
        List performance records for an employee

        Args:
            employee_id: Employee ID
            limit: Maximum records to return
            offset: Number to skip

        Returns:
            List of performance records (newest first)
        """
        result = await self.session.execute(
            select(EmployeePerformanceModel)
            .where(EmployeePerformanceModel.employee_id == str(employee_id))
            .order_by(EmployeePerformanceModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_task(self, task_id: UUID) -> List[EmployeePerformanceModel]:
        """
        List performance records for a specific task

        Args:
            task_id: Task ID

        Returns:
            List of performance records
        """
        result = await self.session.execute(
            select(EmployeePerformanceModel)
            .where(EmployeePerformanceModel.task_id == str(task_id))
            .order_by(EmployeePerformanceModel.timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_recent_performance(
        self,
        employee_id: UUID,
        days: int = 7,
    ) -> List[EmployeePerformanceModel]:
        """
        Get recent performance records for an employee

        Args:
            employee_id: Employee ID
            days: Number of days to look back

        Returns:
            List of recent performance records
        """
        since = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(EmployeePerformanceModel)
            .where(
                EmployeePerformanceModel.employee_id == str(employee_id),
                EmployeePerformanceModel.timestamp >= since,
            )
            .order_by(EmployeePerformanceModel.timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_success_rate(self, employee_id: UUID, days: int = 30) -> float:
        """
        Calculate success rate for an employee

        Args:
            employee_id: Employee ID
            days: Number of days to calculate over

        Returns:
            Success rate (0.0-1.0)
        """
        since = datetime.now(UTC) - timedelta(days=days)

        # Total count
        total_result = await self.session.execute(
            select(func.count())
            .select_from(EmployeePerformanceModel)
            .where(
                EmployeePerformanceModel.employee_id == str(employee_id),
                EmployeePerformanceModel.timestamp >= since,
            )
        )
        total = total_result.scalar_one()

        if total == 0:
            return 0.0

        # Success count
        success_result = await self.session.execute(
            select(func.count())
            .select_from(EmployeePerformanceModel)
            .where(
                EmployeePerformanceModel.employee_id == str(employee_id),
                EmployeePerformanceModel.timestamp >= since,
                EmployeePerformanceModel.success,
            )
        )
        success = success_result.scalar_one()

        return success / total


class EmployeeCostRepository(BaseRepository[EmployeeCostModel]):
    """Repository for EmployeeCost operations"""

    def __init__(self, session: AsyncSession):
        super().__init__(EmployeeCostModel, session)

    async def list_by_employee(
        self,
        employee_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EmployeeCostModel]:
        """
        List cost records for an employee

        Args:
            employee_id: Employee ID
            limit: Maximum records to return
            offset: Number to skip

        Returns:
            List of cost records (newest first)
        """
        result = await self.session.execute(
            select(EmployeeCostModel)
            .where(EmployeeCostModel.employee_id == str(employee_id))
            .order_by(EmployeeCostModel.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_by_task(self, task_id: UUID) -> List[EmployeeCostModel]:
        """
        List cost records for a specific task

        Args:
            task_id: Task ID

        Returns:
            List of cost records
        """
        result = await self.session.execute(
            select(EmployeeCostModel)
            .where(EmployeeCostModel.task_id == str(task_id))
            .order_by(EmployeeCostModel.timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_total_cost(
        self,
        employee_id: UUID,
        days: int = 30,
    ) -> float:
        """
        Calculate total cost for an employee

        Args:
            employee_id: Employee ID
            days: Number of days to calculate over

        Returns:
            Total cost in USD
        """
        since = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(func.sum(EmployeeCostModel.cost_usd)).where(
                EmployeeCostModel.employee_id == str(employee_id),
                EmployeeCostModel.timestamp >= since,
            )
        )
        total = result.scalar_one()

        return total or 0.0

    async def get_total_tokens(
        self,
        employee_id: UUID,
        days: int = 30,
    ) -> dict:
        """
        Calculate total token usage for an employee

        Args:
            employee_id: Employee ID
            days: Number of days to calculate over

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
        """
        since = datetime.now(UTC) - timedelta(days=days)

        result = await self.session.execute(
            select(
                func.sum(EmployeeCostModel.input_tokens),
                func.sum(EmployeeCostModel.output_tokens),
                func.sum(EmployeeCostModel.total_tokens),
            ).where(
                EmployeeCostModel.employee_id == str(employee_id),
                EmployeeCostModel.timestamp >= since,
            )
        )
        input_tokens, output_tokens, total_tokens = result.one()

        return {
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "total_tokens": total_tokens or 0,
        }
