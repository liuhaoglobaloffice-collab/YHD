"""
AI Employee Registry - Central registry for all AI employees.

Single Source of Truth for AI Workforce.
"""

import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationError,
)
from ..database.repositories.converters import employee_to_model, model_to_employee
from ..database.repositories.workforce import AIEmployeeRepository
from .models import AIEmployee, AIEmployeeStatus, Department, Position

logger = logging.getLogger(__name__)


class AIEmployeeRegistry:
    """
    Central registry for AI Employees.

    Single Source of Truth for:
    - Employee identity
    - Employee configuration
    - Employee lifecycle state
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AIEmployeeRepository(session)
        logger.info("AI Employee Registry initialized")

    async def register(self, employee: AIEmployee) -> AIEmployee:
        """
        Register a new AI employee.

        Args:
            employee: AIEmployee instance

        Returns:
            Registered employee

        Raises:
            ConfigurationError: If employee ID or name already exists
            ValidationError: If employee data is invalid
        """
        # Validate
        if not employee.name:
            raise ValidationError("Employee name is required")

        # Check for duplicates
        existing = await self.repo.get_by_id(str(employee.id))
        if existing:
            raise ConfigurationError(f"Employee ID already registered: {employee.id}")

        # Store in database
        model = employee_to_model(employee)
        saved_model = await self.repo.create(model)
        employee = model_to_employee(saved_model)

        logger.info(
            f"Registered AI Employee: {employee.name} "
            f"({employee.department.value}/{employee.position.value})",
            extra={"employee_id": str(employee.id)},
        )

        return employee

    async def get(self, employee_id: UUID) -> AIEmployee:
        """
        Get employee by ID.

        Args:
            employee_id: Employee UUID

        Returns:
            AIEmployee

        Raises:
            ResourceNotFoundError: If employee not found
        """
        model = await self.repo.get_by_id(str(employee_id))
        if not model:
            raise ResourceNotFoundError(f"AI Employee not found: {employee_id}")

        return model_to_employee(model)

    async def get_by_name(self, name: str) -> AIEmployee:
        """
        Get employee by name.

        Args:
            name: Employee name

        Returns:
            AIEmployee

        Raises:
            ResourceNotFoundError: If employee not found
        """
        # Get all employees and filter by name
        models = await self.repo.list_all()
        for model in models:
            if model.name == name:
                return model_to_employee(model)

        raise ResourceNotFoundError(f"AI Employee not found: {name}")

    async def update(self, employee_id: UUID, employee: AIEmployee) -> AIEmployee:
        """
        Update employee.

        Args:
            employee_id: Employee UUID
            employee: Updated employee data

        Returns:
            Updated employee

        Raises:
            ResourceNotFoundError: If employee not found
            ValidationError: If update would create conflicts
        """
        model = await self.repo.get_by_id(str(employee_id))
        if not model:
            raise ResourceNotFoundError(f"AI Employee not found: {employee_id}")

        # Update timestamp
        employee.updated_at = datetime.now(UTC)

        # Update in database
        # Convert employee to dict for update
        model_data = employee_to_model(employee)
        update_dict = {
            "name": model_data.name,
            "department": model_data.department,
            "position": model_data.position,
            "description": model_data.description,
            "agent_type": model_data.agent_type,
            # provider_config is persisted through the provider/model columns
            # (see converters.model_to_employee which reconstructs it on read)
            "provider": model_data.provider,
            "model": model_data.model,
            "status": model_data.status,
            "meta": model_data.meta,
            "updated_at": model_data.updated_at,
        }
        saved_model = await self.repo.update(str(employee_id), update_dict)
        employee = model_to_employee(saved_model)

        logger.info(
            f"Updated AI Employee: {employee.name}", extra={"employee_id": str(employee_id)}
        )

        return employee

    async def delete(self, employee_id: UUID) -> None:
        """
        Delete employee from registry.

        Args:
            employee_id: Employee UUID

        Raises:
            ResourceNotFoundError: If employee not found
        """
        model = await self.repo.get_by_id(str(employee_id))
        if not model:
            raise ResourceNotFoundError(f"AI Employee not found: {employee_id}")

        employee = model_to_employee(model)

        # Delete from database
        await self.repo.delete(str(employee_id))

        logger.info(
            f"Deleted AI Employee: {employee.name}", extra={"employee_id": str(employee_id)}
        )

    async def list_employees(
        self,
        department: Optional[Department] = None,
        position: Optional[Position] = None,
        status: Optional[AIEmployeeStatus] = None,
    ) -> List[AIEmployee]:
        """
        List employees with optional filters.

        Args:
            department: Filter by department
            position: Filter by position
            status: Filter by status

        Returns:
            List of matching employees
        """
        # Get all employees from database
        models = await self.repo.list_all()
        employees = [model_to_employee(m) for m in models]

        if department:
            employees = [e for e in employees if e.department == department]

        if position:
            employees = [e for e in employees if e.position == position]

        if status:
            employees = [e for e in employees if e.status == status]

        return employees

    async def is_registered(self, employee_id: UUID) -> bool:
        """Check if employee is registered."""
        model = await self.repo.get_by_id(str(employee_id))
        return model is not None

    async def count(self) -> int:
        """Get total number of registered employees."""
        models = await self.repo.list_all()
        return len(models)

    async def count_by_status(self) -> dict[AIEmployeeStatus, int]:
        """Get employee counts by status."""
        counts = {status: 0 for status in AIEmployeeStatus}

        models = await self.repo.list_all()
        for model in models:
            employee = model_to_employee(model)
            counts[employee.status] += 1

        return counts

    async def count_by_department(self) -> dict[Department, int]:
        """Get employee counts by department."""
        counts = {dept: 0 for dept in Department}

        models = await self.repo.list_all()
        for model in models:
            employee = model_to_employee(model)
            counts[employee.department] += 1

        return counts
