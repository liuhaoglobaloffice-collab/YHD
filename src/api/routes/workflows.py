"""
Workflow API Routes - Phase 2F-2.5 Service Factory Integration

Architecture (Phase 2F-2.5):
    API Endpoint
        ↓ (Factory Dependency)
    WorkflowService (fully initialized)
        ↓
    WorkflowRepository
        ↓
    Database
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user
from ...api.dependencies.approval import require_approval_for
from ...api.dependencies.database import get_db
from ...api.dependencies.permissions import require_permission
from ...api.factories import get_workflow_service
from ...identity.audit import AuditAction, AuditService
from ...identity.models import User
from ...workflow.executor import WorkflowExecutor
from ...workflow.models import WorkflowExecutionStatus, WorkflowStatus
from ...workflow.service import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ============================================================
# Request/Response Models
# ============================================================


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow definition."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")
    definition: dict = Field(..., description="Workflow definition JSON")


class UpdateWorkflowRequest(BaseModel):
    """Request to update workflow definition."""

    name: str | None = None
    description: str | None = None
    definition: dict | None = None
    status: WorkflowStatus | None = None


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    input_data: dict = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow definition response."""

    id: str
    name: str
    description: str
    definition: dict
    status: WorkflowStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_workflow(cls, workflow):
        # 域对象 Workflow（dataclass）字段为 workflow_id/steps，而非 id/definition；
        # 这里映射为 API 契约（与前端 workflows.ts 的 Workflow 接口一致）
        steps = []
        for step in (workflow.steps or []):
            step_dict = step.to_dict() if hasattr(step, "to_dict") else {
                "step_id": getattr(step, "step_id", None),
                "name": getattr(step, "name", None),
                "description": getattr(step, "description", ""),
            }
            steps.append(step_dict)
        return cls(
            id=str(workflow.workflow_id),
            name=workflow.name,
            description=workflow.description or "",
            definition={
                "steps": steps,
                "required_permissions": getattr(workflow, "required_permissions", []) or [],
                "tags": getattr(workflow, "tags", []) or [],
            },
            status=workflow.status,
            created_at=workflow.created_at.isoformat() if workflow.created_at else "",
            updated_at=workflow.updated_at.isoformat() if workflow.updated_at else "",
        )


class ExecutionResponse(BaseModel):
    """Workflow execution response."""

    id: str
    workflow_id: str
    status: WorkflowExecutionStatus
    input_data: dict
    result: dict | None
    error: str | None
    started_at: str
    completed_at: str | None

    @classmethod
    def from_execution(cls, execution):
        # 域对象 WorkflowExecution 字段为 execution_id/variables，而非 id/input_data
        return cls(
            id=str(execution.execution_id),
            workflow_id=str(execution.workflow_id),
            status=execution.status,
            input_data=execution.variables or {},
            result=execution.result,
            error=execution.error,
            started_at=execution.started_at.isoformat() if execution.started_at else "",
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        )


# ============================================================
# Workflow CRUD Endpoints
# ============================================================


# ==================== 外贸业务模板 ====================
# NOTE: 必须放在 {workflow_id} 路由之前，避免路径冲突


@router.get("/trade-templates", tags=["trade"])
async def list_trade_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """列出外贸业务工作流模板。"""
    from src.workflow.trade_templates import list_trade_templates as _list

    templates = _list(category)
    return {"items": templates, "total": len(templates)}


@router.get("/trade-templates/{template_id}", tags=["trade"])
async def get_trade_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    """获取外贸业务模板详情。"""
    from src.workflow.trade_templates import get_trade_template as _get

    try:
        return _get(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/trade-templates/{template_id}/instantiate", tags=["trade"])
async def instantiate_trade_template(
    template_id: str,
    request: ExecuteWorkflowRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "execute")),
):
    """实例化并执行外贸业务模板。

    将模板转换为工作流定义，并立即执行。
    支持: customer_development, supplier_procurement, deal_closure
    """
    from src.workflow.trade_templates import get_trade_template as _get
    from src.workflow.trade_actions import TradeActionHandler

    try:
        template = _get(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    inputs = request.input_data or {}
    steps = template.get("steps", [])
    step_results = []

    # 依次执行每个步骤
    handler = TradeActionHandler(session, current_user.id)
    for step in steps:
        step_config = {
            **inputs,
            "step_name": step.get("name", ""),
            "step_type": step.get("type", ""),
        }
        result = await handler.execute(step.get("type", ""), step_config)
        step_results.append({
            "name": step.get("name", ""),
            "type": step.get("type", ""),
            "result": result,
        })

    return {
        "template_id": template_id,
        "template_name": template.get("name", ""),
        "status": "completed",
        "inputs": inputs,
        "steps": step_results,
        "total_steps": len(steps),
        "completed_steps": len(step_results),
    }


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "create")),
):
    """
    Create a new workflow definition.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_CREATE permission
    """
    logger.info(f"Create workflow request: {request.name} by user {current_user.id}")

    workflow = await workflow_service.create_workflow(
        name=request.name,
        description=request.description,
        definition=request.definition,
        user=current_user,
    )

    logger.info(f"Workflow created: {workflow.id}")

    # Audit: Workflow created
    await AuditService.log(
        session=session,
        action=AuditAction.WORKFLOW_CREATE,
        resource_type="workflow",
        resource_id=str(workflow.id),
        status="success",
        user_id=current_user.id,
        details={"name": request.name},
    )

    return WorkflowResponse.from_workflow(workflow)


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "read")),
):
    """
    List all workflow definitions.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_READ permission
    """
    logger.info(f"List workflows by user {current_user.id}")

    workflows = await workflow_service.list_workflows(user=current_user)

    return [WorkflowResponse.from_workflow(w) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "read")),
):
    """
    Get workflow definition by ID.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_READ permission
    """
    logger.info(f"Get workflow {workflow_id} by user {current_user.id}")

    workflow = await workflow_service.get_workflow(workflow_id, user=current_user)

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow {workflow_id} not found"
        )

    return WorkflowResponse.from_workflow(workflow)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    request: UpdateWorkflowRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "update")),
):
    """
    Update workflow definition.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_UPDATE permission
    """
    logger.info(f"Update workflow {workflow_id} by user {current_user.id}")

    workflow = await workflow_service.update_workflow(
        workflow_id=workflow_id,
        name=request.name,
        description=request.description,
        definition=request.definition,
        status=request.status,
        user=current_user,
    )

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow {workflow_id} not found"
        )

    logger.info(f"Workflow updated: {workflow_id}")

    # Audit: Workflow updated
    await AuditService.log(
        session=session,
        action=AuditAction.WORKFLOW_UPDATE,
        resource_type="workflow",
        resource_id=str(workflow_id),
        status="success",
        user_id=current_user.id,
        details={"name": request.name, "status": request.status.value if request.status else None},
    )

    return WorkflowResponse.from_workflow(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "delete")),
    _approval: None = Depends(require_approval_for("workflow", "delete")),
):
    """
    Delete workflow definition.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Phase 2 Governance: Approval required for delete operations.
    Requires: WORKFLOW_DELETE permission
    """
    logger.info(f"Delete workflow {workflow_id} by user {current_user.id}")

    deleted = await workflow_service.delete_workflow(workflow_id, user=current_user)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Workflow {workflow_id} not found"
        )

    logger.info(f"Workflow deleted: {workflow_id}")

    # Audit: Workflow deleted
    await AuditService.log(
        session=session,
        action=AuditAction.WORKFLOW_DELETE,
        resource_type="workflow",
        resource_id=str(workflow_id),
        status="success",
        user_id=current_user.id,
        details={"action": "delete"},
    )


# ============================================================
# Workflow Execution Endpoints
# ============================================================


@router.post(
    "/{workflow_id}/execute", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED
)
async def execute_workflow(
    workflow_id: UUID,
    request: ExecuteWorkflowRequest,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "execute")),
):
    """
    Execute a workflow.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_EXECUTE permission

    Note: This endpoint uses WorkflowExecutor internally.
    Future: May need separate execution factory if execution service needs complex dependencies.
    """
    logger.info(f"Execute workflow {workflow_id} by user {current_user.id}")

    # Note: WorkflowExecutor needs session from workflow_service
    # For now, using session directly from workflow_service

    # Get session to create execution service
    # TODO: Consider creating get_workflow_execution_service factory if this becomes complex
    execution_service = WorkflowExecutor(workflow_service.session)

    execution = await execution_service.execute_workflow(
        workflow_id=workflow_id,
        input_data=request.input_data,
        user=current_user,
    )

    logger.info(f"Workflow execution started: {execution.id}")

    # Audit: Workflow executed
    await AuditService.log(
        session=session,
        action=AuditAction.WORKFLOW_EXECUTE,
        resource_type="workflow_execution",
        resource_id=str(execution.id),
        status="success",
        user_id=current_user.id,
        details={"workflow_id": str(workflow_id)},
    )

    return ExecutionResponse.from_execution(execution)


@router.get("/{workflow_id}/executions", response_model=List[ExecutionResponse])
async def list_workflow_executions(
    workflow_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "read")),
):
    """
    List all executions of a workflow.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_READ permission
    """
    logger.info(f"List executions for workflow {workflow_id} by user {current_user.id}")

    execution_service = WorkflowExecutor(workflow_service.session)
    executions = await execution_service.list_executions(
        workflow_id=workflow_id,
        user=current_user,
    )

    return [ExecutionResponse.from_execution(e) for e in executions]


@router.get("/{workflow_id}/executions/{execution_id}", response_model=ExecutionResponse)
async def get_workflow_execution(
    workflow_id: UUID,
    execution_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "read")),
):
    """
    Get workflow execution details.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_READ permission
    """
    logger.info(f"Get execution {execution_id} for workflow {workflow_id}")

    execution_service = WorkflowExecutor(workflow_service.session)
    execution = await execution_service.get_execution(
        execution_id=execution_id,
        user=current_user,
    )

    if not execution or execution.workflow_id != workflow_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found for workflow {workflow_id}",
        )

    return ExecutionResponse.from_execution(execution)


@router.post("/{workflow_id}/executions/{execution_id}/pause", response_model=ExecutionResponse)
async def pause_workflow_execution(
    workflow_id: UUID,
    execution_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "execute")),
):
    """
    Pause a running workflow execution.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_EXECUTE permission
    """
    logger.info(f"Pause execution {execution_id}")

    execution_service = WorkflowExecutor(workflow_service.session)
    execution = await execution_service.pause_execution(
        execution_id=execution_id,
        user=current_user,
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found"
        )

    logger.info(f"Execution paused: {execution_id}")

    return ExecutionResponse.from_execution(execution)


@router.post("/{workflow_id}/executions/{execution_id}/resume", response_model=ExecutionResponse)
async def resume_workflow_execution(
    workflow_id: UUID,
    execution_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "execute")),
):
    """
    Resume a paused workflow execution.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_EXECUTE permission
    """
    logger.info(f"Resume execution {execution_id}")

    execution_service = WorkflowExecutor(workflow_service.session)
    execution = await execution_service.resume_execution(
        execution_id=execution_id,
        user=current_user,
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found"
        )

    logger.info(f"Execution resumed: {execution_id}")

    return ExecutionResponse.from_execution(execution)


@router.post("/{workflow_id}/executions/{execution_id}/cancel", response_model=ExecutionResponse)
async def cancel_workflow_execution(
    workflow_id: UUID,
    execution_id: UUID,
    workflow_service: WorkflowService = Depends(get_workflow_service),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("workflow", "execute")),
):
    """
    Cancel a workflow execution.

    Phase 2F-2.5: Uses factory dependency for service instantiation.
    Requires: WORKFLOW_EXECUTE permission
    """
    logger.info(f"Cancel execution {execution_id}")

    execution_service = WorkflowExecutor(workflow_service.session)
    execution = await execution_service.cancel_execution(
        execution_id=execution_id,
        user=current_user,
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Execution {execution_id} not found"
        )

    logger.info(f"Execution cancelled: {execution_id}")

    return ExecutionResponse.from_execution(execution)
