"""
Workforce API Routes - Phase 2F-2.5 Service Factory Integration

Architecture (Phase 2F-2.5):
    API Endpoint
        ↓ (Factory Dependency)
    AIEmployeeService (fully initialized)
        ↓
    AIEmployeeRegistry
        ↓
    Database

Stage 6: External AI Workforce management endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai.agents import AgentType
from ...api.dependencies import get_current_user
from ...api.dependencies.database import get_db
from ...api.dependencies.permissions import require_permission
from ...api.factories import get_workforce_service
from ...core.errors import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from ...identity.audit import AuditAction, AuditService
from ...identity.models import User
from ...workforce.employee import AIEmployeeService
from ...workforce.models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    Position,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workforce", tags=["workforce"])


# ============================================================
# Request/Response Schemas
# ============================================================


class CreateEmployeeRequest(BaseModel):
    """Create AI employee request."""

    name: str = Field(..., min_length=1, max_length=255)
    department: Department
    position: Position
    description: str = Field(..., min_length=1, max_length=2000)
    agent_type: Optional[AgentType] = None


class UpdateEmployeeRequest(BaseModel):
    """Update AI employee request."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    status: Optional[AIEmployeeStatus] = None


class EmployeeResponse(BaseModel):
    """AI employee response."""

    id: str
    name: str
    department: str
    position: str
    description: str
    agent_type: Optional[str]
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_employee(cls, employee: AIEmployee):
        return cls(
            id=str(employee.id),
            name=employee.name,
            department=employee.department.value,
            position=employee.position.value,
            description=employee.description or "",
            agent_type=employee.agent_type.value if employee.agent_type else None,
            status=employee.status.value,
            created_at=employee.created_at.isoformat(),
            updated_at=employee.updated_at.isoformat(),
        )


class PerformanceResponse(BaseModel):
    """AI employee performance response."""

    employee_id: str
    tasks_completed: int
    tasks_failed: int
    success_rate: float
    total_execution_time: float
    average_execution_time: float


class CostResponse(BaseModel):
    """AI employee cost response."""

    employee_id: str
    total_cost_usd: float
    api_calls: int
    tokens_used: int


# ============================================================
# Employee CRUD Endpoints
# ============================================================


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    request: CreateEmployeeRequest,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "create")),
):
    """
    Create a new AI employee.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_CREATE permission
    """
    logger.info(f"Create AI employee request: {request.name} by user {current_user.id}")

    try:
        employee = await employee_service.create_employee(
            name=request.name,
            department=request.department,
            position=request.position,
            description=request.description,
            agent_type=request.agent_type,
            actor_id=current_user.id,
        )

        logger.info(f"AI employee created: {employee.id}")

        # Audit: Employee created
        await AuditService.log(
            session=session,
            action=AuditAction.EMPLOYEE_CREATED,
            resource_type="ai_employee",
            resource_id=str(employee.id),
            status="success",
            user_id=current_user.id,
            details={
                "name": request.name,
                "department": request.department.value,
                "position": request.position.value,
            },
        )

        return EmployeeResponse.from_employee(employee)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    department: Optional[Department] = None,
    position: Optional[Position] = None,
    status_filter: Optional[AIEmployeeStatus] = None,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """
    List AI employees with optional filters.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_READ permission
    """
    logger.info(f"List AI employees by user {current_user.id}")

    try:
        employees = await employee_service.list_employees(actor_id=current_user.id)

        if department:
            employees = [e for e in employees if e.department == department]
        if position:
            employees = [e for e in employees if e.position == position]
        if status_filter:
            employees = [e for e in employees if e.status == status_filter]

        return [EmployeeResponse.from_employee(e) for e in employees]

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """
    Get AI employee by ID.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_READ permission
    """
    logger.info(f"Get AI employee {employee_id} by user {current_user.id}")

    try:
        employee = await employee_service.get_employee(employee_id, actor_id=current_user.id)

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        return EmployeeResponse.from_employee(employee)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    request: UpdateEmployeeRequest,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "update")),
):
    """
    Update AI employee.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_UPDATE permission
    """
    logger.info(f"Update AI employee {employee_id} by user {current_user.id}")

    try:
        employee = await employee_service.update_employee(
            employee_id=employee_id,
            name=request.name,
            description=request.description,
            status=request.status,
            actor_id=current_user.id,
        )

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        logger.info(f"AI employee updated: {employee_id}")

        # Audit: Employee updated
        await AuditService.log(
            session=session,
            action=AuditAction.EMPLOYEE_UPDATED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=current_user.id,
            details={
                "name": request.name,
                "status": request.status.value if request.status else None,
            },
        )

        return EmployeeResponse.from_employee(employee)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/employees/{employee_id}/activate", response_model=EmployeeResponse)
async def activate_employee(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Activate an AI employee.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_UPDATE permission
    """
    logger.info(f"Activate AI employee {employee_id} by user {current_user.id}")

    try:
        employee = await employee_service.update_employee(
            employee_id=employee_id,
            status=AIEmployeeStatus.ACTIVE,
            actor_id=current_user.id,
        )

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        logger.info(f"AI employee activated: {employee_id}")

        # Audit: Employee activated
        await AuditService.log(
            session=session,
            action=AuditAction.EMPLOYEE_ACTIVATED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=current_user.id,
            details={"action": "activate"},
        )

        return EmployeeResponse.from_employee(employee)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/employees/{employee_id}/performance", response_model=PerformanceResponse)
async def get_employee_performance(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("employee", "performance_read")),
):
    """
    Get performance summary for an employee.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_READ permission
    """
    logger.info(f"Get performance for AI employee {employee_id}")

    try:
        employee = await employee_service.get_employee(employee_id, actor_id=current_user.id)

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        # TODO: Implement actual performance tracking
        return PerformanceResponse(
            employee_id=str(employee_id),
            tasks_completed=0,
            tasks_failed=0,
            success_rate=0.0,
            total_execution_time=0.0,
            average_execution_time=0.0,
        )

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/employees/{employee_id}/cost", response_model=CostResponse)
async def get_employee_cost(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("employee", "cost_read")),
):
    """
    Get cost summary for an employee.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFORCE_READ permission
    """
    logger.info(f"Get cost for AI employee {employee_id}")

    try:
        employee = await employee_service.get_employee(employee_id, actor_id=current_user.id)

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        # TODO: Implement actual cost tracking
        return CostResponse(
            employee_id=str(employee_id),
            total_cost_usd=0.0,
            api_calls=0,
            tokens_used=0,
        )

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
