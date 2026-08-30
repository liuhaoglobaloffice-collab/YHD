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
import os
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...ai.agents import AgentType
from ...ai.cost_tracker import CostTracker
from ...ai.memory_store import AgentMemoryStore
from ...api.dependencies import get_current_user
from ...api.dependencies.database import get_db
from ...api.dependencies.permissions import require_permission
from ...api.factories import get_workforce_service
from ...core.errors import (
    PermissionDeniedError,
    ResourceNotFoundError,
    ValidationError,
)
from ...database.models import AiCostRecordModel, BusinessTaskModel
from ...identity.audit import AuditAction, AuditService
from ...ai.agent_router import AgentRouter
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
    # 允许创建时即指定 Provider/模型覆盖（如 ollama 本地模型），执行时优先生效
    provider_config: Optional[Dict[str, Any]] = None


class UpdateEmployeeRequest(BaseModel):
    """Update AI employee request."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    status: Optional[AIEmployeeStatus] = None
    # 允许更新 Provider/模型覆盖（如 ollama 本地模型），执行时优先生效
    provider_config: Optional[Dict[str, Any]] = None


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
    trust_score: Optional[float] = None
    capability_score: Optional[float] = None
    risk_score: Optional[float] = None

    @classmethod
    async def from_employee(cls, employee: AIEmployee, session = None):
        trust = capability = risk = None
        if session is not None:
            try:
                from ...ai.agent_router import AgentRouter
                router = AgentRouter(session)
                eid = str(employee.id)
                trust = await router.get_agent_trust_score(eid)
                capability = await router.get_agent_capability_score(eid)
                risk = await router.get_agent_risk_score(eid)
            except Exception as e:
                logger.warning(f"Failed to load trust scores for employee {employee.id}: {e}")
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
            trust_score=trust,
            capability_score=capability,
            risk_score=risk,
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


class ExecuteTaskRequest(BaseModel):
    """Execute AI employee task request."""

    prompt: str = Field(..., min_length=1, max_length=10000)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)


class ExecuteTaskResponse(BaseModel):
    """Execute AI employee task response."""

    execution_id: str
    employee_id: str
    employee_name: str
    agent_type: str
    status: str
    output: Optional[str] = None
    error: Optional[str] = None
    response_time_ms: Optional[float] = None


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
            provider_config=request.provider_config,
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

        return await EmployeeResponse.from_employee(employee, session)

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
    session: AsyncSession = Depends(get_db),
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

        return [await EmployeeResponse.from_employee(e, session) for e in employees]

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
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

        return await EmployeeResponse.from_employee(employee, session)

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
            provider_config=request.provider_config,
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
                "provider_config_updated": request.provider_config is not None,
            },
        )

        return await EmployeeResponse.from_employee(employee, session)

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

        return await EmployeeResponse.from_employee(employee, session)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================================================================
# P1-G2.2: 老板手动干预 AI 员工（暂停 / 恢复 / 信任 override）
# ==================================================================


@router.post("/employees/{employee_id}/suspend", response_model=EmployeeResponse)
async def suspend_employee(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "update")),
):
    """
    Suspend an AI employee (P1-G2.2 老板干预)。

    Requires: WORKFORCE_UPDATE permission
    """
    logger.info(f"Suspend AI employee {employee_id} by user {current_user.id}")

    try:
        employee = await employee_service.update_employee(
            employee_id=employee_id,
            status=AIEmployeeStatus.SUSPENDED,
            actor_id=current_user.id,
        )
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee {employee_id} not found"
            )

        await AuditService.log(
            session=session,
            action=AuditAction.EMPLOYEE_SUSPENDED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=current_user.id,
            details={"action": "suspend"},
        )
        return await EmployeeResponse.from_employee(employee, session)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/employees/{employee_id}/resume", response_model=EmployeeResponse)
async def resume_employee(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "update")),
):
    """
    Resume a suspended AI employee (P1-G2.2 老板干预)。

    Requires: WORKFORCE_UPDATE permission
    """
    logger.info(f"Resume AI employee {employee_id} by user {current_user.id}")

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

        await AuditService.log(
            session=session,
            action=AuditAction.EMPLOYEE_ACTIVATED,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            status="success",
            user_id=current_user.id,
            details={"action": "resume"},
        )
        return await EmployeeResponse.from_employee(employee, session)

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/employees/{employee_id}/trust-override")
async def trust_override_endpoint(
    employee_id: UUID,
    body: Dict[str, Any],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "update")),
):
    """
    手动设置 AI 员工信任评分 override（P1-G2.2）。

    Body: {"score": 0.0-1.0, "reason": "..."}
    持久化到 ai_employees.meta.trust_override（override_source=MANUAL，可追溯）。
    score 越界返回 400（fail-closed）。
    """
    logger.info(f"Trust override for employee {employee_id} by user {current_user.id}")

    score = body.get("score")
    reason = body.get("reason", "")
    if not isinstance(score, (int, float)):
        raise HTTPException(status_code=400, detail="score 必须为数字")

    router = AgentRouter(session)
    try:
        override = await router.set_trust_override(
            employee_id=str(employee_id),
            score=float(score),
            reason=reason,
            actor_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await AuditService.log(
        session=session,
        action=AuditAction.UPDATE,
        resource_type="ai_employee",
        resource_id=str(employee_id),
        status="success",
        user_id=current_user.id,
        details={"action": "trust_override", "score": score, "reason": reason},
    )
    return {"employee_id": str(employee_id), "override": override}


@router.delete("/employees/{employee_id}/trust-override")
async def trust_override_clear_endpoint(
    employee_id: UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "update")),
):
    """清除手动信任 override，恢复动态信任计算（P1-G2.2）。"""
    logger.info(f"Clear trust override for employee {employee_id} by user {current_user.id}")

    router = AgentRouter(session)
    try:
        cleared = await router.clear_trust_override(str(employee_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await AuditService.log(
        session=session,
        action=AuditAction.UPDATE,
        resource_type="ai_employee",
        resource_id=str(employee_id),
        status="success",
        user_id=current_user.id,
        details={"action": "trust_override_cleared", "cleared": cleared},
    )
    return {"employee_id": str(employee_id), "cleared": cleared}


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

        # Query BusinessTaskModel for real task statistics
        stmt = select(BusinessTaskModel).where(
            BusinessTaskModel.assigned_employee_id == str(employee_id)
        )
        rows = list((await employee_service.registry.session.execute(stmt)).scalars().all())

        tasks_completed = sum(1 for r in rows if r.status == "completed")
        tasks_failed = sum(1 for r in rows if r.status == "failed")
        total = tasks_completed + tasks_failed
        success_rate = tasks_completed / total if total > 0 else 0.0

        # Calculate execution time from completed tasks
        total_execution_time = 0.0
        for r in rows:
            if r.status == "completed" and r.completed_at and r.created_at:
                delta = (r.completed_at - r.created_at).total_seconds()
                total_execution_time += delta

        average_execution_time = total_execution_time / tasks_completed if tasks_completed > 0 else 0.0

        return PerformanceResponse(
            employee_id=str(employee_id),
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            success_rate=round(success_rate, 2),
            total_execution_time=round(total_execution_time, 2),
            average_execution_time=round(average_execution_time, 2),
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

        # Query AiCostRecordModel for real cost data
        stmt = select(
            func.count(AiCostRecordModel.id),
            func.coalesce(func.sum(AiCostRecordModel.cost_usd), 0),
            func.coalesce(func.sum(AiCostRecordModel.total_tokens), 0),
        ).where(AiCostRecordModel.employee_id == str(employee_id))

        result = await employee_service.registry.session.execute(stmt)
        row = result.one()

        api_calls = row[0]
        total_cost = float(row[1])
        total_tokens = row[2] if row[2] else 0

        return CostResponse(
            employee_id=str(employee_id),
            total_cost_usd=round(total_cost, 6),
            api_calls=api_calls,
            tokens_used=total_tokens,
        )

    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/employees/{employee_id}/execute", response_model=ExecuteTaskResponse)
async def execute_employee_task(
    employee_id: UUID,
    request: ExecuteTaskRequest,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Execute a task using an AI employee's assigned agent.

    Bridges the AI Employee system with the Agent Runtime and Provider Gateway
    to call the real LLM (OpenAI, Ollama, etc.) based on the employee's agent type.

    Requires: AGENT_EXECUTE permission
    """
    # V4: 月度预算拦截（超限拒绝执行）
    await _enforce_ai_budget(session, current_user)

    logger.info(
        f"Execute task for AI employee {employee_id} by user {current_user.id}",
        extra={"prompt_length": len(request.prompt)},
    )

    try:
        result = await employee_service.execute_task(
            employee_id=employee_id,
            prompt=request.prompt,
            actor_id=current_user.id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        logger.info(
            f"Task execution completed: {result.get('employee_name')} "
            f"(status={result.get('status')}, "
            f"execution_id={result.get('execution_id')})",
        )

        return ExecuteTaskResponse(
            execution_id=result["execution_id"],
            employee_id=result["employee_id"],
            employee_name=result["employee_name"],
            agent_type=result["agent_type"],
            status=result["status"],
            output=result.get("output"),
            error=result.get("error"),
            response_time_ms=result.get("response_time_ms"),
        )

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}",
        )


class ProviderStatusResponse(BaseModel):
    """Provider status response."""

    provider: str
    model: str
    available: bool
    description: str
    providers: List[Dict[str, Any]] = []


@router.post("/employees/{employee_id}/execute/stream")
async def execute_employee_task_stream(
    employee_id: UUID,
    request: ExecuteTaskRequest,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Execute a task using an AI employee's assigned agent with streaming output.

    Returns an NDJSON stream of {"delta": str} chunks followed by a final
    {"done": true, "output": str} marker. Client should read line-by-line.

    Requires: AGENT_EXECUTE permission
    """
    # V4: 月度预算拦截（超限拒绝执行）
    await _enforce_ai_budget(session, current_user)

    from fastapi.responses import StreamingResponse
    import json as _json

    async def event_stream():
        try:
            async for chunk in employee_service.execute_task_stream(
                employee_id=employee_id,
                prompt=request.prompt,
                actor_id=current_user.id,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield _json.dumps(chunk, ensure_ascii=False) + "\n"
        except Exception as e:
            yield _json.dumps({"delta": "", "error": str(e), "done": True, "output": ""}) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ============================================================
# Async Execution Queue (P2)
# ============================================================


class ExecutionOut(BaseModel):
    """Async execution record response."""

    task_id: str
    employee_id: str
    employee_name: str
    agent_type: str
    prompt: str
    status: str
    output: str = ""
    error: Optional[str] = None
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    elapsed_ms: Optional[float] = None


class ExecutionListOut(BaseModel):
    """List of execution records."""

    executions: List[ExecutionOut]
    total: int


async def _enforce_ai_budget(session: AsyncSession, user: User) -> None:
    """AI 执行前的月度预算检查（V4）：超限则拒绝执行。"""
    if not user or user.ai_budget_monthly is None:
        return
    check = await CostTracker(session).check_budget(user.id)
    if not check["allow"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"本月 AI 预算已用完（${check['used_usd']:.4f} / ${check['budget']}），"
                "已拦截任务执行，请联系主账号调整预算"
            ),
        )


def _to_execution_out(record) -> ExecutionOut:
    d = record.to_dict()
    return ExecutionOut(
        task_id=d["task_id"],
        employee_id=d["employee_id"],
        employee_name=d["employee_name"],
        agent_type=d["agent_type"],
        prompt=d["prompt"],
        status=d["status"],
        output=d.get("output", ""),
        error=d.get("error"),
        created_at=d.get("created_at"),
        started_at=d.get("started_at"),
        completed_at=d.get("completed_at"),
        elapsed_ms=d.get("elapsed_ms"),
    )


@router.post("/employees/{employee_id}/tasks", response_model=ExecutionOut)
async def submit_async_task(
    employee_id: UUID,
    request: ExecuteTaskRequest,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Submit an AI employee task to the async execution queue.

    Returns immediately with a task_id. Client polls GET /workforce/tasks/{id}
    for status and output. This avoids blocking HTTP for long LLM calls.
    """
    # V4: 月度预算拦截（超限拒绝入队）
    await _enforce_ai_budget(session, current_user)

    from src.workforce.execution_queue import ExecutionStatus, get_execution_queue

    # Resolve employee info
    employee = await employee_service.get_employee(employee_id, actor_id=current_user.id)
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    queue = get_execution_queue()

    async def run_fn(record) -> None:
        # 复用流式执行逻辑，把增量写入 record
        async for chunk in employee_service.execute_task_stream(
            employee_id=employee_id,
            prompt=request.prompt,
            actor_id=current_user.id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        ):
            if chunk.get("delta"):
                record.output += chunk["delta"]
            if chunk.get("error"):
                record.error = chunk["error"]
            if chunk.get("done"):
                break
        if not record.error:
            record.status = ExecutionStatus.COMPLETED
        else:
            record.status = ExecutionStatus.FAILED
        record.completed_at = time.time()

    record = await queue.submit(
        employee_id=employee_id,
        employee_name=employee.name,
        agent_type=employee.agent_type.value if employee.agent_type else "",
        prompt=request.prompt,
        run_fn=run_fn,
    )
    return _to_execution_out(record)


@router.get("/tasks/{task_id}", response_model=ExecutionOut)
async def get_execution(
    task_id: str,
    _: User = Depends(get_current_user),
    __: None = Depends(require_permission("agent", "read")),
):
    """Get async execution status/output by task_id."""
    from src.workforce.execution_queue import get_execution_queue

    record = get_execution_queue().get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Execution {task_id} not found")
    return _to_execution_out(record)


@router.get("/tasks", response_model=ExecutionListOut)
async def list_executions(
    limit: int = 50,
    status: Optional[str] = None,
    _: User = Depends(get_current_user),
    __: None = Depends(require_permission("agent", "read")),
):
    """List recent async executions (optionally filtered by status)."""
    from src.workforce.execution_queue import get_execution_queue

    records = get_execution_queue().list(limit=limit, status=status)
    return ExecutionListOut(
        executions=[_to_execution_out(r) for r in records],
        total=len(records),
    )


@router.delete("/tasks/{task_id}")
async def cancel_execution(
    task_id: str,
    _: User = Depends(get_current_user),
    __: None = Depends(require_permission("agent", "execute")),
):
    """Cancel a queued/running async execution."""
    from src.workforce.execution_queue import get_execution_queue

    cancelled = await get_execution_queue().cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Execution {task_id} not found")
    return {"status": "cancelled", "task_id": task_id}


@router.get("/provider/status", response_model=ProviderStatusResponse)
async def get_provider_status(
    _: User = Depends(get_current_user),
    __: None = Depends(require_permission("agent", "read")),
):
    """
    Get the current LLM provider status.

    Returns the configured provider type, model, and availability.
    Supports multiple providers (comma-separated LLM_PROVIDER).
    """
    from src.ai.gateway import get_gateway
    from src.ai.providers import ProviderType
    from src.api.provider_catalog import _PROVIDER_CATALOG

    gateway = get_gateway()
    raw = os.getenv("LLM_PROVIDER", "mock").lower().strip()
    provider_names = [p.strip() for p in raw.split(",") if p.strip()]

    # Build provider status for each configured provider
    providers_status = []
    available = False
    primary_model = "mock"
    primary_description = "Mock 模式（开发测试）"

    for name in provider_names:
        if name == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "")
            model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            prov_avail = bool(api_key)
            desc = "OpenAI 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            model = os.getenv("ANTHROPIC_CHAT_MODEL", "claude-3-5-sonnet-20241022")
            prov_avail = bool(api_key)
            desc = "Anthropic Claude 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "google":
            api_key = os.getenv("GOOGLE_API_KEY", "")
            model = os.getenv("GOOGLE_CHAT_MODEL", "gemini-1.5-flash")
            prov_avail = bool(api_key)
            desc = "Google Gemini 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY", "")
            model = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
            prov_avail = bool(api_key)
            desc = "DeepSeek 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "xai":
            api_key = os.getenv("XAI_API_KEY", "")
            model = os.getenv("XAI_CHAT_MODEL", "grok-2")
            prov_avail = bool(api_key)
            desc = "xAI Grok 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "moonshot":
            api_key = os.getenv("MOONSHOT_API_KEY", "")
            model = os.getenv("MOONSHOT_CHAT_MODEL", "moonshot-v1-8k")
            prov_avail = bool(api_key)
            desc = "Moonshot Kimi 云服务" if prov_avail else "未配置 API Key"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

        elif name == "ollama":
            ollama_enabled = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
            model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
            prov_avail = False
            if ollama_enabled:
                try:
                    import httpx
                    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                    resp = await httpx.AsyncClient(timeout=3.0).get(f"{ollama_host}/api/tags")
                    prov_avail = resp.status_code == 200
                except Exception:
                    prov_avail = False
            desc = "Ollama 本地模型" if prov_avail else "Ollama 未运行或模型未就绪"
            providers_status.append({"provider": name, "model": model, "available": prov_avail, "description": desc})
            if prov_avail and not available:
                available = True
                primary_model = model
                primary_description = desc

    # If no providers are configured, show mock
    if not providers_status:
        providers_status.append({
            "provider": "mock",
            "model": "mock",
            "available": True,
            "description": "Mock 模式（开发测试）",
        })

    return ProviderStatusResponse(
        provider=raw,
        model=primary_model,
        available=available,
        description=primary_description,
        providers=providers_status,
    )


# ============================================================
# AI 记忆层（V3）：会话记忆查询 / 清空
# ============================================================


class AgentMemoryOut(BaseModel):
    """Agent 记忆条目响应。"""

    id: int
    role: str
    content: str
    task_id: Optional[str] = None
    created_at: Optional[str] = None


@router.get(
    "/employees/{employee_id}/memories", response_model=List[AgentMemoryOut]
)
async def list_agent_memories(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """查看当前用户与该 AI 员工的对话记忆（时间正序）。"""
    store = AgentMemoryStore(employee_service.registry.session)
    rows = await store.recall(current_user.id, str(employee_id), limit=100)
    return [
        AgentMemoryOut(
            id=m.id,
            role=m.role,
            content=m.content,
            task_id=m.task_id,
            created_at=m.created_at.isoformat(),
        )
        for m in rows
    ]


@router.delete("/employees/{employee_id}/memories")
async def clear_agent_memories(
    employee_id: UUID,
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
):
    """清空当前用户与该 AI 员工的对话记忆（仅限自己的记忆，无需额外权限）。"""
    store = AgentMemoryStore(employee_service.registry.session)
    deleted = await store.forget(current_user.id, str(employee_id))
    return {"deleted": deleted}


# ============================================================
# AI 成本追踪（V3 · 能量系统落地）
# ============================================================


class CostRecordOut(BaseModel):
    """成本记录条目。"""

    id: int
    provider: str
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: Optional[float] = None
    status: str = "success"
    employee_id: Optional[str] = None
    agent_type: Optional[str] = None
    created_at: Optional[str] = None


class CostSummaryOut(BaseModel):
    """成本聚合。"""

    days: int
    total_requests: int
    total_cost_usd: float
    total_tokens: int
    avg_latency_ms: float
    failed_requests: int
    by_provider: dict


@router.get("/costs", response_model=List[CostRecordOut])
async def list_costs(
    limit: int = Query(50, ge=1, le=200),
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """查看最近 AI 调用成本记录。"""
    from ...ai.cost_tracker import CostTracker

    store = CostTracker(employee_service.registry.session)
    rows = await store.list_records(current_user.id, limit=limit)
    return [
        CostRecordOut(
            id=r.id,
            provider=r.provider,
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            total_tokens=r.total_tokens,
            cost_usd=r.cost_usd,
            latency_ms=r.latency_ms,
            status=r.status,
            employee_id=r.employee_id,
            agent_type=r.agent_type,
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.get("/costs/summary", response_model=CostSummaryOut)
async def cost_summary(
    days: int = Query(7, ge=1, le=90),
    employee_service: AIEmployeeService = Depends(get_workforce_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("agent", "read")),
):
    """查看近 N 天 AI 调用成本汇总（累计成本/请求/Token/耗时）。"""
    from ...ai.cost_tracker import CostTracker

    store = CostTracker(employee_service.registry.session)
    return await store.summary(current_user.id, days=days)
