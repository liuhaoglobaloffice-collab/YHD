"""
AI Tools API routes - Tool execution and approval flow
"""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.dependencies.permissions import require_permission
from src.ai.tools import ToolCategory, ToolExecution, ToolRegistry, ToolStatus
from src.core.errors import ResourceNotFoundError, ValidationError
from src.governance.approval import ApprovalService
from src.governance.risk import RiskEvaluator
from src.identity.audit import AuditService
from src.identity.database import get_db_session
from src.identity.models import User
from src.security.policy import PolicyEngine

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    tool_id: str
    parameters: Dict[str, Any] = {}
    trace_id: str
    agent_type: Optional[str] = None
    actor_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class ToolExecuteApprovedRequest(BaseModel):
    """Request to execute an approved tool."""

    execution_id: str
    approval_id: str
    trace_id: str
    actor_id: Optional[str] = None


class ToolExecutionResponse(BaseModel):
    """Tool execution response."""

    execution_id: str
    tool_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    approval_id: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ToolListResponse(BaseModel):
    """Tool list response."""

    tools: list[dict]
    total: int


def _execution_to_response(execution: ToolExecution) -> ToolExecutionResponse:
    """Convert ToolExecution dataclass to response model."""
    return ToolExecutionResponse(
        execution_id=str(execution.execution_id),
        tool_id=execution.tool_id,
        status=execution.status.value,
        result=execution.result,
        error=execution.error,
        approval_id=str(execution.approval_id) if execution.approval_id else None,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
    )


def _build_tool_registry(session: AsyncSession) -> ToolRegistry:
    """Build a ToolRegistry instance with required dependencies."""
    return ToolRegistry(
        audit_service=AuditService(),
        policy_engine=PolicyEngine(),
        approval_service=ApprovalService(session),
        risk_evaluator=RiskEvaluator(),
        session=session,
        rbac_service=None,
    )


@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Execute a tool with full security enforcement.

    Low-risk tools execute immediately.
    High-risk tools that require approval will return PENDING status with an approval_id.
    """
    registry = _build_tool_registry(session)

    try:
        execution = await registry.execute(
            tool_id=request.tool_id,
            parameters=request.parameters,
            trace_id=UUID(request.trace_id),
            agent_type=request.agent_type,
            actor_id=UUID(request.actor_id) if request.actor_id else None,
            idempotency_key=request.idempotency_key,
        )
        return _execution_to_response(execution)
    except (ResourceNotFoundError, ValidationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/execute-approved", response_model=ToolExecutionResponse)
async def execute_approved_tool(
    request: ToolExecuteApprovedRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    _: None = Depends(require_permission("agent", "execute")),
):
    """
    Execute a tool after it has been approved.

    Verifies the approval is still valid, then executes the tool.
    """
    registry = _build_tool_registry(session)

    try:
        execution = await registry.execute_approved(
            execution_id=UUID(request.execution_id),
            approval_id=request.approval_id,
            trace_id=UUID(request.trace_id),
            actor_id=UUID(request.actor_id) if request.actor_id else None,
        )
        return _execution_to_response(execution)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("", response_model=ToolListResponse)
async def list_tools(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """List registered tools, optionally filtered by category."""
    registry = _build_tool_registry(session)
    cat = ToolCategory(category) if category else None
    tools = registry.list_tools(category=cat, enabled_only=True)
    return ToolListResponse(
        tools=[{"tool_id": t.tool_id, "name": t.name, "description": t.description, "category": t.category.value} for t in tools],
        total=len(tools),
    )