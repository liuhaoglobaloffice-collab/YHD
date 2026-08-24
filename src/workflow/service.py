"""
Workflow Service - CRUD operations for workflow definitions.

Security: All operations require RBAC permissions and are audited.
"""

import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.di import get_dependency
from ..database.repositories.converters import _step_to_dict, model_to_workflow, workflow_to_model
from ..database.repositories.workflow import WorkflowRepository
from ..identity.audit import AuditAction, AuditService
from ..identity.models import User
from ..identity.rbac import Permission, RBACService
from .models import Workflow, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Workflow definition management service.

    Responsibilities:
    - Create/Read/Update/Delete workflow definitions
    - Validate workflow structure
    - Enforce RBAC and audit all operations
    """

    def __init__(
        self,
        session: AsyncSession,
        rbac_service: Optional[RBACService] = None,
        audit_service: Optional[AuditService] = None,
    ):
        self.session = session
        self.repo = WorkflowRepository(session)
        self.rbac = rbac_service or get_dependency(RBACService)
        self.audit = audit_service or get_dependency(AuditService)
        logger.info("WorkflowService initialized")

    async def create_workflow(
        self,
        name: str,
        description: str,
        steps: List[dict],
        user: User,
        status: WorkflowStatus = WorkflowStatus.DRAFT,
        required_permissions: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Workflow:
        """
        Create new workflow definition.

        Args:
            name: Workflow name
            description: Workflow description
            steps: List of workflow steps (will be converted to WorkflowStep objects)
            context: Security context
            status: Initial status
            required_permissions: Permissions required to execute workflow
            tags: Workflow tags
            metadata: Additional metadata

        Returns:
            Created workflow

        Raises:
            PermissionError: If user lacks permission
            ValueError: If workflow validation fails
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_CREATE):
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_CREATE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=None,
                status="DENIED",
                details={"reason": "Missing WORKFLOW_CREATE permission"},
            )
            raise PermissionError("Permission denied: WORKFLOW_CREATE required")

        # Import here to avoid circular dependency

        # Convert step dicts to WorkflowStep objects
        workflow_steps = []
        for step_data in steps:
            step = self._dict_to_step(step_data)
            workflow_steps.append(step)

        # Create workflow
        workflow = Workflow(
            name=name,
            description=description,
            status=status,
            steps=workflow_steps,
            created_by=user.id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            required_permissions=required_permissions or [],
            tags=tags or [],
            metadata=metadata or {},
        )

        # Validate workflow
        errors = workflow.validate()
        if errors:
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_CREATE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow.workflow_id),
                status="FAILED",
                details={"errors": errors},
            )
            raise ValueError(f"Workflow validation failed: {errors}")

        # Store workflow in database
        model = workflow_to_model(workflow)
        saved_model = await self.repo.create(model)
        workflow = model_to_workflow(saved_model)

        # Audit success
        await self.audit.log(
            self.session,
            action=AuditAction.WORKFLOW_CREATE,
            user_id=user.id,
            resource_type="workflow",
            resource_id=str(workflow.workflow_id),
            status="SUCCESS",
            details={
                "name": name,
                "status": status.value,
                "step_count": len(steps),
            },
        )

        logger.info(f"Workflow created: {workflow.workflow_id} - {name}")
        return workflow

    def _dict_to_step(self, step_data: dict):
        """Convert step dict to WorkflowStep object."""
        from .models import WorkflowStep, WorkflowStepType

        # Normalize step_type to uppercase
        step_type_str = str(step_data["step_type"]).upper()

        # Extract nested steps
        sub_steps = []
        if "steps" in step_data:
            for sub_step_data in step_data["steps"]:
                sub_steps.append(self._dict_to_step(sub_step_data))

        true_steps = []
        if "true_steps" in step_data:
            for sub_step_data in step_data["true_steps"]:
                true_steps.append(self._dict_to_step(sub_step_data))

        false_steps = []
        if "false_steps" in step_data:
            for sub_step_data in step_data["false_steps"]:
                false_steps.append(self._dict_to_step(sub_step_data))

        return WorkflowStep(
            step_id=step_data["step_id"],
            step_type=WorkflowStepType(step_type_str),
            name=step_data["name"],
            description=step_data.get("description", ""),
            task_type=step_data.get("task_type"),
            task_config=step_data.get("task_config", {}),
            steps=sub_steps,
            condition=step_data.get("condition"),
            true_steps=true_steps,
            false_steps=false_steps,
            loop_condition=step_data.get("loop_condition"),
            max_iterations=step_data.get("max_iterations", 10),
            timeout_seconds=step_data.get("timeout_seconds"),
            max_retries=step_data.get("max_retries", 0),
            retry_delay_seconds=step_data.get("retry_delay_seconds", 5),
            required_permissions=step_data.get("required_permissions", []),
        )

    async def get_workflow(
        self,
        workflow_id: UUID,
        user: User,
    ) -> Optional[Workflow]:
        """
        Get workflow by ID.

        Args:
            workflow_id: Workflow ID
            context: Security context

        Returns:
            Workflow or None if not found

        Raises:
            PermissionError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_READ):
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_READ,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="DENIED",
                details={"reason": "Missing WORKFLOW_READ permission"},
            )
            raise PermissionError("Permission denied: WORKFLOW_READ required")

        model = await self.repo.get_by_id(str(workflow_id))
        workflow = model_to_workflow(model) if model else None

        if workflow:
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_READ,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="SUCCESS",
            )

        return workflow

    async def list_workflows(
        self,
        user: User,
        status: Optional[WorkflowStatus] = None,
        created_by: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Workflow]:
        """
        List workflows with optional filters.

        Args:
            context: Security context
            status: Filter by status
            created_by: Filter by creator
            tags: Filter by tags (workflow must have all specified tags)

        Returns:
            List of workflows

        Raises:
            PermissionError: If user lacks permission
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_READ):
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_LIST,
                user_id=user.id,
                resource_type="workflow",
                resource_id=None,
                status="DENIED",
                details={"reason": "Missing WORKFLOW_READ permission"},
            )
            raise PermissionError("Permission denied: WORKFLOW_READ required")

        # Get all workflows from database
        models = await self.repo.list_all()
        workflows = [model_to_workflow(m) for m in models]

        # Apply filters
        if status:
            workflows = [w for w in workflows if w.status == status]

        if created_by:
            workflows = [w for w in workflows if w.created_by == created_by]

        if tags:
            workflows = [w for w in workflows if all(tag in w.tags for tag in tags)]

        await self.audit.log(
            self.session,
            action=AuditAction.WORKFLOW_LIST,
            user_id=user.id,
            resource_type="workflow",
            resource_id=None,
            status="SUCCESS",
            details={"count": len(workflows)},
        )

        return workflows

    async def update_workflow(
        self,
        workflow_id: UUID,
        user: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        steps: Optional[List[dict]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> Workflow:
        """
        Update workflow definition.

        Args:
            workflow_id: Workflow ID
            context: Security context
            name: New name (optional)
            description: New description (optional)
            status: New status (optional)
            steps: New steps (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)

        Returns:
            Updated workflow

        Raises:
            PermissionError: If user lacks permission
            ValueError: If workflow not found or validation fails
        """
        # Check permission
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_UPDATE):
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_UPDATE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="DENIED",
                details={"reason": "Missing WORKFLOW_UPDATE permission"},
            )
            raise PermissionError("Permission denied: WORKFLOW_UPDATE required")

        # Get existing workflow
        model = await self.repo.get_by_id(str(workflow_id))
        if not model:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = model_to_workflow(model)

        # Update fields
        changes = {}

        if name is not None:
            changes["name"] = {"old": workflow.name, "new": name}
            workflow.name = name

        if description is not None:
            changes["description"] = {"old": workflow.description, "new": description}
            workflow.description = description

        if status is not None:
            changes["status"] = {"old": workflow.status.value, "new": status.value}
            workflow.status = status

        if steps is not None:
            workflow_steps = []
            for step_data in steps:
                step = self._dict_to_step(step_data)
                workflow_steps.append(step)
            changes["steps"] = {"old_count": len(workflow.steps), "new_count": len(workflow_steps)}
            workflow.steps = workflow_steps

        if tags is not None:
            changes["tags"] = {"old": workflow.tags, "new": tags}
            workflow.tags = tags

        if metadata is not None:
            changes["metadata"] = {"updated": True}
            workflow.metadata.update(metadata)

        workflow.updated_at = datetime.now(UTC)

        # Validate updated workflow
        errors = workflow.validate()
        if errors:
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_UPDATE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="FAILED",
                details={"errors": errors},
            )
            raise ValueError(f"Workflow validation failed: {errors}")

        # Update in database
        # Convert workflow to dict of updates
        update_dict = {
            "name": workflow.name,
            "description": workflow.description,
            "enabled": (workflow.status == WorkflowStatus.ACTIVE),
            "steps": [_step_to_dict(step) for step in workflow.steps],
            "tags": workflow.tags,
            "context": {
                "status": workflow.status.value,
                "required_permissions": workflow.required_permissions,
                "meta": workflow.metadata,
            },
            "updated_at": workflow.updated_at,
        }
        saved_model = await self.repo.update(str(workflow_id), update_dict)
        workflow = model_to_workflow(saved_model)

        # Audit success
        await self.audit.log(
            self.session,
            action=AuditAction.WORKFLOW_UPDATE,
            user_id=user.id,
            resource_type="workflow",
            resource_id=str(workflow_id),
            status="SUCCESS",
            details={"changes": changes},
        )

        logger.info(f"Workflow updated: {workflow_id}")
        return workflow

    async def delete_workflow(
        self,
        workflow_id: UUID,
        user: User,
    ) -> bool:
        """
        Delete workflow definition.

        Args:
            workflow_id: Workflow ID
            context: Security context

        Returns:
            True if deleted, False if not found

        Raises:
            PermissionError: If user lacks permission
        """
        # Check permission (requires ADMIN role)
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_DELETE):
            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_DELETE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="DENIED",
                details={"reason": "Missing WORKFLOW_DELETE permission"},
            )
            raise PermissionError("Permission denied: WORKFLOW_DELETE required")

        # Get workflow for audit info
        model = await self.repo.get_by_id(str(workflow_id))

        if model:
            workflow = model_to_workflow(model)
            await self.repo.delete(str(workflow_id))

            await self.audit.log(
                self.session,
                action=AuditAction.WORKFLOW_DELETE,
                user_id=user.id,
                resource_type="workflow",
                resource_id=str(workflow_id),
                status="SUCCESS",
                details={"name": workflow.name},
            )
            logger.info(f"Workflow deleted: {workflow_id}")
            return True

        return False

    async def validate_workflow(
        self,
        workflow_id: UUID,
        user: User,
    ) -> List[str]:
        """
        Validate workflow definition.

        Args:
            workflow_id: Workflow ID
            context: Security context

        Returns:
            List of validation errors (empty if valid)

        Raises:
            PermissionError: If user lacks permission
            ValueError: If workflow not found
        """
        if not await self.rbac.check_permission_by_id(user.id, Permission.WORKFLOW_READ):
            raise PermissionError("Permission denied: WORKFLOW_READ required")

        model = await self.repo.get_by_id(str(workflow_id))
        if not model:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow = model_to_workflow(model)

        return workflow.validate()
