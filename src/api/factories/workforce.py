"""
Workforce Service Factory

Phase 2F-2.5: Dependency injection factory for AIEmployeeService.

Handles:
- AIEmployeeRegistry instantiation
- RBACService creation
- AuditService integration (static)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.workforce.employee import AIEmployeeService
from src.workforce.registry import AIEmployeeRegistry


async def get_workforce_service(
    session: AsyncSession = Depends(get_db),
) -> AIEmployeeService:
    """
    Create AIEmployeeService with all dependencies.

    Phase 2F-2.5: Service Factory Pattern

    Dependencies injected:
    - AIEmployeeRegistry(session)
    - RBACService(session)
    - AuditService (static class)

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured AIEmployeeService instance
    """
    registry = AIEmployeeRegistry(session)
    rbac_service = RBACService(session)

    return AIEmployeeService(
        registry=registry,
        rbac_service=rbac_service,
        audit_service=AuditService,  # Static service
    )
