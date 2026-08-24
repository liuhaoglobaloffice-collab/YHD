"""
AI Employee Cost Tracker.

Tracks token usage and API costs for AI employees.
"""

import logging
from datetime import UTC, datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from .models import EmployeeCostRecord
from .registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Tracks AI Employee costs and token usage.

    Metrics:
    - Token usage (input/output)
    - API costs (USD)
    - Cost per task
    - Total spend
    - ROI calculations
    """

    def __init__(self, registry: AIEmployeeRegistry):
        self.registry = registry
        self._records: Dict[UUID, List[EmployeeCostRecord]] = {}  # employee_id -> records
        logger.info("Cost Tracker initialized")

    async def record_cost(
        self,
        employee_id: UUID,
        provider: str,
        model_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_cost_usd: float = 0.0,
        output_cost_usd: float = 0.0,
        task_id: Optional[UUID] = None,
        workflow_id: Optional[UUID] = None,
        metadata: Optional[Dict] = None,
    ) -> EmployeeCostRecord:
        """
        Record cost for an AI employee operation.

        Args:
            employee_id: Employee UUID
            provider: Provider name (e.g., "openai", "anthropic")
            model_id: Model ID used
            input_tokens: Input tokens consumed
            output_tokens: Output tokens consumed
            input_cost_usd: Input cost in USD
            output_cost_usd: Output cost in USD
            task_id: Task UUID (optional)
            workflow_id: Workflow UUID (optional)
            metadata: Additional metadata

        Returns:
            Created cost record

        Raises:
            ResourceNotFoundError: If employee not found
        """
        # Verify employee exists
        employee = await self.registry.get(employee_id)

        # Create record
        total_tokens = input_tokens + output_tokens
        total_cost = input_cost_usd + output_cost_usd

        record = EmployeeCostRecord(
            id=uuid4(),
            employee_id=employee_id,
            task_id=task_id,
            workflow_id=workflow_id,
            provider=provider,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost_usd=input_cost_usd,
            output_cost_usd=output_cost_usd,
            total_cost_usd=total_cost,
            metadata=metadata or {},
        )

        # Store record
        if employee_id not in self._records:
            self._records[employee_id] = []
        self._records[employee_id].append(record)

        # Update employee total cost
        employee.total_cost_usd += total_cost
        employee.updated_at = datetime.now(UTC)
        await self.registry.update(employee_id, employee)

        logger.info(
            f"Recorded cost for {employee.name}: "
            f"{total_tokens} tokens, ${total_cost:.4f} ({provider}/{model_id})",
            extra={
                "employee_id": str(employee_id),
                "task_id": str(task_id),
                "provider": provider,
                "model": model_id,
            },
        )

        return record

    async def get_employee_costs(
        self,
        employee_id: UUID,
    ) -> List[EmployeeCostRecord]:
        """
        Get all cost records for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            List of cost records
        """
        # Verify employee exists
        await self.registry.get(employee_id)

        return self._records.get(employee_id, [])

    async def get_cost_summary(
        self,
        employee_id: UUID,
    ) -> Dict:
        """
        Get cost summary for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            Cost summary dictionary
        """
        employee = await self.registry.get(employee_id)
        records = self._records.get(employee_id, [])

        total_input_tokens = sum(r.input_tokens for r in records)
        total_output_tokens = sum(r.output_tokens for r in records)
        total_tokens = sum(r.total_tokens for r in records)

        total_input_cost = sum(r.input_cost_usd for r in records)
        total_output_cost = sum(r.output_cost_usd for r in records)
        total_cost = employee.total_cost_usd

        # Calculate averages
        num_tasks = employee.tasks_completed + employee.tasks_failed
        avg_cost_per_task = total_cost / num_tasks if num_tasks > 0 else 0.0
        avg_tokens_per_task = total_tokens / num_tasks if num_tasks > 0 else 0.0

        # Provider breakdown
        provider_breakdown = {}
        for record in records:
            if record.provider not in provider_breakdown:
                provider_breakdown[record.provider] = {
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "calls": 0,
                }
            provider_breakdown[record.provider]["tokens"] += record.total_tokens
            provider_breakdown[record.provider]["cost_usd"] += record.total_cost_usd
            provider_breakdown[record.provider]["calls"] += 1

        return {
            "employee_id": str(employee_id),
            "employee_name": employee.name,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_tokens,
            "total_input_cost_usd": total_input_cost,
            "total_output_cost_usd": total_output_cost,
            "total_cost_usd": total_cost,
            "average_cost_per_task_usd": avg_cost_per_task,
            "average_tokens_per_task": avg_tokens_per_task,
            "total_records": len(records),
            "provider_breakdown": provider_breakdown,
        }

    async def get_total_system_cost(self) -> Dict:
        """
        Get total system-wide cost across all employees.

        Returns:
            System-wide cost summary
        """
        total_employees = await self.registry.count()
        total_cost = 0.0
        total_tokens = 0
        total_tasks = 0

        provider_totals = {}

        employees = await self.registry.list_employees()
        for employee in employees:
            employee_id = employee.id
            try:
                total_cost += employee.total_cost_usd
                total_tasks += employee.tasks_completed + employee.tasks_failed

                records = self._records.get(employee_id, [])
                total_tokens += sum(r.total_tokens for r in records)

                # Provider aggregation
                for record in records:
                    if record.provider not in provider_totals:
                        provider_totals[record.provider] = {
                            "tokens": 0,
                            "cost_usd": 0.0,
                            "calls": 0,
                        }
                    provider_totals[record.provider]["tokens"] += record.total_tokens
                    provider_totals[record.provider]["cost_usd"] += record.total_cost_usd
                    provider_totals[record.provider]["calls"] += 1
            except Exception as e:
                logger.warning(f"Failed to get costs for {employee_id}: {e}")

        avg_cost_per_employee = total_cost / total_employees if total_employees > 0 else 0.0
        avg_cost_per_task = total_cost / total_tasks if total_tasks > 0 else 0.0

        return {
            "total_employees": total_employees,
            "total_tasks": total_tasks,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "average_cost_per_employee_usd": avg_cost_per_employee,
            "average_cost_per_task_usd": avg_cost_per_task,
            "provider_breakdown": provider_totals,
        }

    async def get_most_expensive_employees(
        self,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Get most expensive employees by total cost.

        Args:
            limit: Maximum number of results

        Returns:
            List of employee cost summaries sorted by cost
        """
        summaries = []

        employees = await self.registry.list_employees()
        for employee in employees:
            employee_id = employee.id
            try:
                summary = await self.get_cost_summary(employee_id)
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to get cost summary for {employee_id}: {e}")

        # Sort by total cost
        summaries.sort(key=lambda s: s["total_cost_usd"], reverse=True)

        return summaries[:limit]

    def clear_records(self, employee_id: UUID) -> None:
        """
        Clear all cost records for an employee.

        Args:
            employee_id: Employee UUID
        """
        if employee_id in self._records:
            del self._records[employee_id]
            logger.info(f"Cleared cost records for {employee_id}")
