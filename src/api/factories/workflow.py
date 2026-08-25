"""
Workflow Service Factory

Phase 2F-2.5: Dependency injection factory for WorkflowService.

Handles:
- AsyncSession injection
- RBACService creation
- AuditService integration (optional)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.identity.rbac import RBACService
from src.workflow.service import WorkflowService


async def get_workflow_service(
    session: AsyncSession = Depends(get_db),
) -> WorkflowService:
    """
    Create WorkflowService with dependencies.

    Phase 2F-2.5: Service Factory Pattern

    Dependencies injected:
    - AsyncSession (for repository access)
    - RBACService(session) (optional)

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured WorkflowService instance
    """
    rbac_service = RBACService(session)

    return WorkflowService(
        session=session,
        rbac_service=rbac_service,
    )
