"""
Business OS API Routes - Phase 2F-2.5 Service Factory Integration

REST API endpoints for business operations.

Architecture (Phase 2F-2.5):
    API Endpoint
        ↓ (Factory Dependency)
    BusinessService (fully initialized)
        ↓
    BusinessRepository
        ↓
    Database
"""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.database import get_db
from src.api.dependencies.permissions import require_permission
from src.api.factories import get_business_service
from src.business.models import (
    BusinessDomain,
    BusinessTaskPriority,
    BusinessTaskStatus,
)
from src.business.service import BusinessService
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/business", tags=["business"])


@router.post("/tasks", response_model=dict)
async def create_task(
    domain: BusinessDomain,
    title: str,
    description: str,
    priority: BusinessTaskPriority = BusinessTaskPriority.MEDIUM,
    context: Optional[dict] = None,
    tags: Optional[List[str]] = None,
    business_service: BusinessService = Depends(get_business_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("business", "task_create")),
):
    """
    Create a business task.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    task = await business_service.create_task(
        user_id=current_user.id,
        domain=domain,
        title=title,
        description=description,
        priority=priority,
        context=context,
        tags=tags,
    )

    # Audit: Business task created
    await AuditService.log(
        session=session,
        action=AuditAction.BUSINESS_TASK_CREATED,
        resource_type="business_task",
        resource_id=str(task.id),
        status="success",
        user_id=current_user.id,
        details={"domain": domain.value, "title": title, "priority": priority.value},
    )

    return task.to_dict()


@router.get("/tasks", response_model=list)
async def list_tasks(
    domain: Optional[BusinessDomain] = None,
    status: Optional[BusinessTaskStatus] = None,
    priority: Optional[BusinessTaskPriority] = None,
    assigned_employee_id: Optional[UUID] = None,
    business_service: BusinessService = Depends(get_business_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("business", "read")),
):
    """
    List business tasks with filters.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    tasks = await business_service.list_tasks(
        user_id=current_user.id,
        domain=domain,
        status=status,
        priority=priority,
        assigned_employee_id=assigned_employee_id,
    )
    return [task.to_dict() for task in tasks]


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task(
    task_id: UUID,
    business_service: BusinessService = Depends(get_business_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("business", "read")),
):
    """
    Get a business task by ID.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    task = await business_service.get_task(
        user_id=current_user.id,
        task_id=task_id,
    )

    if not task:
        raise HTTPException(status_code=404, detail=f"Business task not found: {task_id}")

    return task.to_dict()


@router.put("/tasks/{task_id}", response_model=dict)
async def update_task(
    task_id: UUID,
    status: Optional[BusinessTaskStatus] = None,
    priority: Optional[BusinessTaskPriority] = None,
    assigned_employee_id: Optional[UUID] = None,
    result: Optional[dict] = None,
    business_service: BusinessService = Depends(get_business_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("business", "task_update")),
):
    """
    Update a business task.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    task = await business_service.update_task(
        user_id=current_user.id,
        task_id=task_id,
        status=status,
        priority=priority,
        assigned_employee_id=assigned_employee_id,
        result=result,
    )

    # Audit: Business task updated
    await AuditService.log(
        session=session,
        action=AuditAction.BUSINESS_TASK_UPDATED,
        resource_type="business_task",
        resource_id=str(task_id),
        status="success",
        user_id=current_user.id,
        details={
            "status": status.value if status else None,
            "priority": priority.value if priority else None,
            "assigned_employee_id": str(assigned_employee_id) if assigned_employee_id else None,
        },
    )

    return task.to_dict()


@router.get("/metrics", response_model=dict)
async def get_metrics(
    domain: Optional[BusinessDomain] = None,
    business_service: BusinessService = Depends(get_business_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("business", "metrics_read")),
):
    """
    Get business metrics.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    """
    metrics = await business_service.get_metrics(
        user_id=current_user.id,
        domain=domain,
    )
    return metrics.to_dict()
