"""
AI Brain API Routes - Phase 3.1

REST API endpoints for AI Brain command processing.

Architecture:
    API Endpoint
        ↓
    AIBrain (orchestrator)
        ↓
    Command Processing → Task Planning → Agent Routing
        ↓
    Workflow Engine
        ↓
    Task Execution
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.models import CommandPriority, CommandStatus
from src.ai.orchestrator import AIBrain
from src.api.dependencies import get_current_user, get_db, require_permission_dependency
from src.identity.audit import AuditAction, AuditService
from src.identity.models import User
from src.identity.rbac import Permission

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai-brain", tags=["AI Brain"])


# Request/Response Models
class CommandRequest(BaseModel):
    """CEO Command request"""

    command: str = Field(..., description="Natural language command", min_length=1, max_length=5000)
    priority: Optional[CommandPriority] = Field(
        default=CommandPriority.NORMAL, description="Command priority level"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context for command execution"
    )


class CommandResponse(BaseModel):
    """CEO Command response"""

    command_id: UUID
    status: CommandStatus
    goal: Optional[str] = None
    task_count: Optional[int] = None
    workflow_id: Optional[UUID] = None
    message: str


class CommandStatusResponse(BaseModel):
    """Command status response"""

    command_id: UUID
    command_text: str
    status: CommandStatus
    priority: CommandPriority
    goal: Optional[str] = None
    task_plan: Optional[List[Dict[str, Any]]] = None
    agent_assignments: Optional[List[Dict[str, Any]]] = None
    workflow_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class CommandListResponse(BaseModel):
    """List of commands response"""

    commands: List[CommandStatusResponse]
    total: int


@router.post(
    "/command",
    response_model=CommandResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission_dependency(Permission.AI_BRAIN_COMMAND_EXECUTE))],
)
async def submit_ceo_command(
    request: CommandRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CommandResponse:
    """
    Submit a CEO command for AI Brain processing.

    **Security**: Requires AI_BRAIN_COMMAND_EXECUTE permission.

    **Audit**: Generates AI_BRAIN_COMMAND_CREATED event.

    **Flow**:
    1. Parse natural language command
    2. Generate task plan
    3. Route to appropriate AI agents
    4. Create workflow execution
    5. Return command ID and status

    **Example**:
    ```json
    {
        "command": "分析越南食品包装市场",
        "priority": "HIGH"
    }
    ```
    """
    logger.info(
        "ceo_command_received",
        user_id=str(user.id),
        command_length=len(request.command),
        priority=request.priority,
    )

    try:
        # Initialize AI Brain
        brain = AIBrain(session)

        # Process command
        command = await brain.process_command(
            command_text=request.command,
            user=user,
            priority=request.priority,
            context=request.context or {},
        )

        # Audit log
        audit_service = AuditService(session)
        await audit_service.log(
            session,
            user_id=user.id,
            action=AuditAction.AI_BRAIN_COMMAND_CREATED,
            resource_type="ai_brain_command",
            resource_id=str(command.command_id),
            status="success",
            details={
                "command": request.command[:200],  # Truncate for audit
                "priority": request.priority.value,
                "status": command.status.value,
            },
        )

        logger.info(
            "ceo_command_processed",
            command_id=str(command.command_id),
            status=command.status,
            goal=command.goal,
        )

        return CommandResponse(
            command_id=command.command_id,
            status=command.status,
            goal=command.goal,
            task_count=len(command.task_plan) if command.task_plan else 0,
            workflow_id=command.workflow_id,
            message=f"Command processed successfully. Status: {command.status.value}",
        )

    except ValueError as e:
        logger.warning("invalid_command", error=str(e), user_id=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid command: {str(e)}",
        )
    except Exception as e:
        logger.error(
            "command_processing_failed",
            error=str(e),
            user_id=str(user.id),
            exc_info=True,
        )

        # Audit failure
        audit_service = AuditService(session)
        await audit_service.log(
            session,
            user_id=user.id,
            action=AuditAction.AI_BRAIN_COMMAND_CREATED,
            resource_type="ai_brain_command",
            resource_id="unknown",
            status="failure",
            error_message=str(e),
            details={"command": request.command[:200], "error": str(e)},
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process command. Please try again.",
        )


@router.get(
    "/commands/{command_id}",
    response_model=CommandStatusResponse,
    dependencies=[Depends(require_permission_dependency(Permission.AI_BRAIN_PLAN_READ))],
)
async def get_command_status(
    command_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CommandStatusResponse:
    """
    Get the status of a specific CEO command.

    **Security**: Requires AI_BRAIN_PLAN_READ permission.

    **Returns**: Command details including task plan and agent assignments.
    """
    logger.info("get_command_status", command_id=str(command_id), user_id=str(user.id))

    try:
        brain = AIBrain(session)
        command = await brain.get_command_status(command_id)

        if not command:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Command {command_id} not found",
            )

        return CommandStatusResponse(
            command_id=command.command_id,
            command_text=command.command_text,
            status=command.status,
            priority=command.priority,
            goal=command.goal,
            task_plan=command.task_plan,
            agent_assignments=command.agent_assignments,
            workflow_id=command.workflow_id,
            created_at=command.created_at,
            updated_at=command.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_command_status_failed",
            command_id=str(command_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve command status",
        )


@router.get(
    "/commands",
    response_model=CommandListResponse,
    dependencies=[Depends(require_permission_dependency(Permission.AI_BRAIN_PLAN_READ))],
)
async def list_commands(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    status_filter: Optional[CommandStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> CommandListResponse:
    """
    List CEO commands.

    **Security**: Requires AI_BRAIN_PLAN_READ permission.

    **Filters**:
    - status: Filter by command status
    - limit: Maximum number of results (default 50)
    - offset: Pagination offset (default 0)
    """
    logger.info(
        "list_commands",
        user_id=str(user.id),
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )

    try:
        brain = AIBrain(session)
        commands = await brain.list_commands(
            user_id=user.id,
            status_filter=status_filter,
            limit=limit,
            offset=offset,
        )

        total = await brain.get_commands_count(
            user_id=user.id,
            status_filter=status_filter,
        )

        command_responses = [
            CommandStatusResponse(
                command_id=cmd.command_id,
                command_text=cmd.command_text,
                status=cmd.status,
                priority=cmd.priority,
                goal=cmd.goal,
                task_plan=cmd.task_plan,
                agent_assignments=cmd.agent_assignments,
                workflow_id=cmd.workflow_id,
                created_at=cmd.created_at,
                updated_at=cmd.updated_at,
            )
            for cmd in commands
        ]

        return CommandListResponse(commands=command_responses, total=total)

    except Exception as e:
        logger.error("list_commands_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list commands",
        )


@router.delete(
    "/commands/{command_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission_dependency(Permission.AI_BRAIN_COMMAND_EXECUTE))],
)
async def cancel_command(
    command_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    Cancel a pending CEO command.

    **Security**: Requires AI_BRAIN_COMMAND_EXECUTE permission.

    **Note**: Only commands in PENDING or PLANNING status can be cancelled.
    """
    logger.info("cancel_command", command_id=str(command_id), user_id=str(user.id))

    try:
        brain = AIBrain(session)
        success = await brain.cancel_command(command_id, user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Command cannot be cancelled (not found or already executing)",
            )

        # Audit log
        audit_service = AuditService(session)
        await audit_service.log(
            session,
            user_id=user.id,
            action=AuditAction.AI_BRAIN_COMMAND_CANCELLED,
            resource_type="ai_brain_command",
            resource_id=str(command_id),
            status="success",
            details={"action": "cancelled"},
        )

        logger.info("command_cancelled", command_id=str(command_id))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "cancel_command_failed",
            command_id=str(command_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel command",
        )
