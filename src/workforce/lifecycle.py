"""
AI Employee Lifecycle Manager.

Manages employee state transitions:
    CREATED → TRAINING → ACTIVE → SUSPENDED → RETIRED
"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from ..core.errors import (
    PermissionDeniedError,
    ValidationError,
)
from ..identity.audit import AuditAction, AuditService
from ..identity.rbac import RBACService, has_permission
from .models import AIEmployee, AIEmployeeStatus
from .registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class EmployeeLifecycleManager:
    """
    Manages AI Employee lifecycle state transitions.

    State Machine:
        CREATED → TRAINING → ACTIVE ⇄ SUSPENDED → RETIRED

    Enforces:
    - Valid state transitions only
    - RBAC checks for lifecycle operations
    - Audit all state changes
    """

    PERM_EMPLOYEE_ACTIVATE = "employee:activate"
    PERM_EMPLOYEE_SUSPEND = "employee:suspend"
    PERM_EMPLOYEE_RETIRE = "employee:retire"

    # Valid state transitions
    VALID_TRANSITIONS = {
        AIEmployeeStatus.CREATED: {AIEmployeeStatus.TRAINING, AIEmployeeStatus.ACTIVE},
        AIEmployeeStatus.TRAINING: {AIEmployeeStatus.ACTIVE, AIEmployeeStatus.RETIRED},
        AIEmployeeStatus.ACTIVE: {AIEmployeeStatus.SUSPENDED, AIEmployeeStatus.RETIRED},
        AIEmployeeStatus.SUSPENDED: {AIEmployeeStatus.ACTIVE, AIEmployeeStatus.RETIRED},
        AIEmployeeStatus.RETIRED: set(),  # Terminal state
    }

    def __init__(
        self,
        registry: AIEmployeeRegistry,
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        self.registry = registry
        self.rbac = rbac_service
        self.audit = audit_service
        logger.info("Employee Lifecycle Manager initialized")

    async def activate(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> AIEmployee:
        """
        Activate an AI employee (make them ready to work).

        Args:
            employee_id: Employee UUID
            actor_id: User activating the employee

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ValidationError: If activation is not valid
        """
        # RBAC check
        if actor_id and not has_permission(actor_id, self.PERM_EMPLOYEE_ACTIVATE, self.rbac):
            raise PermissionDeniedError(
                f"User {actor_id} lacks permission: {self.PERM_EMPLOYEE_ACTIVATE}"
            )

        # Get employee
        employee = await self.registry.get(employee_id)

        # Validate transition
        if employee.status == AIEmployeeStatus.ACTIVE:
            logger.warning(f"Employee {employee.name} is already active")
            return employee

        if AIEmployeeStatus.ACTIVE not in self.VALID_TRANSITIONS.get(employee.status, set()):
            raise ValidationError(f"Cannot activate employee in status: {employee.status.value}")

        # Validate configuration
        if not employee.agent_type:
            raise ValidationError("Cannot activate employee without assigned agent")

        # Update status
        old_status = employee.status
        employee.status = AIEmployeeStatus.ACTIVE
        employee.activated_at = datetime.now(UTC)
        employee.updated_at = datetime.now(UTC)

        # Update registry
        employee = await self.registry.update(employee_id, employee)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.UPDATE,
            status="success",
            resource_type="ai_employee",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "lifecycle_action": "activate",
                "old_status": old_status.value,
                "new_status": employee.status.value,
            },
        )

        logger.info(
            f"Activated AI Employee: {employee.name}",
            extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
        )

        return employee

    async def suspend(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AIEmployee:
        """
        Suspend an AI employee (temporarily disable).

        Args:
            employee_id: Employee UUID
            actor_id: User suspending the employee
            reason: Suspension reason

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ValidationError: If suspension is not valid
        """
        # RBAC check
        if actor_id and not has_permission(actor_id, self.PERM_EMPLOYEE_SUSPEND, self.rbac):
            raise PermissionDeniedError(
                f"User {actor_id} lacks permission: {self.PERM_EMPLOYEE_SUSPEND}"
            )

        # Get employee
        employee = await self.registry.get(employee_id)

        # Validate transition
        if employee.status == AIEmployeeStatus.SUSPENDED:
            logger.warning(f"Employee {employee.name} is already suspended")
            return employee

        if AIEmployeeStatus.SUSPENDED not in self.VALID_TRANSITIONS.get(employee.status, set()):
            raise ValidationError(f"Cannot suspend employee in status: {employee.status.value}")

        # Update status
        old_status = employee.status
        employee.status = AIEmployeeStatus.SUSPENDED
        employee.suspended_at = datetime.now(UTC)
        employee.updated_at = datetime.now(UTC)

        if reason:
            employee.metadata["suspension_reason"] = reason

        # Update registry
        employee = await self.registry.update(employee_id, employee)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.UPDATE,
            status="success",
            resource_type="ai_employee",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "lifecycle_action": "suspend",
                "old_status": old_status.value,
                "new_status": employee.status.value,
                "reason": reason,
            },
        )

        logger.info(
            f"Suspended AI Employee: {employee.name}",
            extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
        )

        return employee

    async def retire(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> AIEmployee:
        """
        Retire an AI employee (permanently disable).

        Args:
            employee_id: Employee UUID
            actor_id: User retiring the employee
            reason: Retirement reason

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ValidationError: If retirement is not valid
        """
        # RBAC check
        if actor_id and not has_permission(actor_id, self.PERM_EMPLOYEE_RETIRE, self.rbac):
            raise PermissionDeniedError(
                f"User {actor_id} lacks permission: {self.PERM_EMPLOYEE_RETIRE}"
            )

        # Get employee
        employee = await self.registry.get(employee_id)

        # Validate transition
        if employee.status == AIEmployeeStatus.RETIRED:
            logger.warning(f"Employee {employee.name} is already retired")
            return employee

        if AIEmployeeStatus.RETIRED not in self.VALID_TRANSITIONS.get(employee.status, set()):
            raise ValidationError(f"Cannot retire employee in status: {employee.status.value}")

        # Update status
        old_status = employee.status
        employee.status = AIEmployeeStatus.RETIRED
        employee.retired_at = datetime.now(UTC)
        employee.updated_at = datetime.now(UTC)

        if reason:
            employee.metadata["retirement_reason"] = reason

        # Update registry
        employee = await self.registry.update(employee_id, employee)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.UPDATE,
            status="success",
            resource_type="ai_employee",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "lifecycle_action": "retire",
                "old_status": old_status.value,
                "new_status": employee.status.value,
                "reason": reason,
            },
        )

        logger.info(
            f"Retired AI Employee: {employee.name}",
            extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
        )

        return employee

    def can_transition(
        self,
        from_status: AIEmployeeStatus,
        to_status: AIEmployeeStatus,
    ) -> bool:
        """
        Check if a status transition is valid.

        Args:
            from_status: Current status
            to_status: Target status

        Returns:
            True if transition is valid
        """
        return to_status in self.VALID_TRANSITIONS.get(from_status, set())
