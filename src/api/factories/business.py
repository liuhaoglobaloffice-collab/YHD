"""
Business Service Factory

Phase 2F-2.5: Dependency injection factory for BusinessService.

Handles:
- BusinessTaskRegistry instantiation
- AIEmployeeRegistry instantiation
- RBACService creation
- AuditService integration (static)
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import get_db
from src.business.registry import BusinessTaskRegistry
from src.business.service import BusinessService
from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.workforce.registry import AIEmployeeRegistry


async def get_business_service(
    session: AsyncSession = Depends(get_db),
) -> BusinessService:
    """
    Create BusinessService with all dependencies.

    Phase 2F-2.5: Service Factory Pattern

    Dependencies injected:
    - BusinessTaskRegistry(session)
    - AIEmployeeRegistry(session)
    - RBACService(session)
    - AuditService (static class)

    Args:
        session: Database session from dependency injection

    Returns:
        Fully configured BusinessService instance
    """
    task_registry = BusinessTaskRegistry(session)
    employee_registry = AIEmployeeRegistry(session)
    rbac_service = RBACService(session)

    return BusinessService(
        task_registry=task_registry,
        employee_registry=employee_registry,
        rbac_service=rbac_service,
        audit_service=AuditService,  # Static service
    )
