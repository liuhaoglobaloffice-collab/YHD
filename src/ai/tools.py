"""
Tool Registry - Unified tool management and execution.

Enforces: All tool calls go through RBAC, Policy, Approval, and Audit.
Single Source of Truth for tool permissions and execution.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.errors import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationError,
)
from ..governance.approval import ApprovalService
from ..governance.risk import RiskEvaluator, RiskLevel
from ..identity.audit import AuditService
from ..identity.models import ApprovalStatus
from ..identity.rbac import RBACService
from ..security.policy import PolicyAction, PolicyEngine

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Tool categories."""

    SYSTEM = "system"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    COMMUNICATION = "communication"
    DATA = "data"
    EXTERNAL = "external"


class ToolStatus(str, Enum):
    """Tool execution status."""

    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"


@dataclass
class ToolConfig:
    """Tool configuration."""

    tool_id: str
    name: str
    description: str
    category: ToolCategory
    risk_level: RiskLevel
    requires_approval: bool = False
    required_permissions: Set[str] = field(default_factory=set)
    allowed_agents: Set[str] = field(default_factory=lambda: {"*"})  # "*" = all agents
    rate_limit_per_hour: Optional[int] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecution:
    """Tool execution record."""

    execution_id: UUID
    tool_id: str
    agent_type: Optional[str]
    actor_id: Optional[UUID]
    trace_id: UUID
    status: ToolStatus
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    approval_id: Optional[UUID] = None
    risk_level: Optional[RiskLevel] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None  # Prevent duplicate execution
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """
    Unified Tool Registry with security enforcement.

    Enforces:
    - Security First: All tools require permission checks
    - Approval First: High-risk tools require approval
    - Fail Closed: Unknown tools denied
    - Audit Everything: All executions audited
    - No Duplicate Execution: Idempotency key support
    """

    def __init__(
        self,
        audit_service: AuditService,
        policy_engine: PolicyEngine,
        approval_service: ApprovalService,
        risk_evaluator: RiskEvaluator,
        session: Optional[AsyncSession] = None,
        rbac_service: Optional[RBACService] = None,
    ):
        self._tools: Dict[str, ToolConfig] = {}
        self._handlers: Dict[str, Callable] = {}
        self._audit_service = audit_service
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._risk_evaluator = risk_evaluator
        self._session = session
        self._rbac_service = rbac_service
        self._executions: Dict[str, ToolExecution] = {}  # idempotency tracking
        self._rate_limits: Dict[str, List[datetime]] = {}
        logger.info("Tool Registry initialized")

    def register_tool(self, config: ToolConfig, handler: Callable):
        """Register a tool with its handler."""
        if config.tool_id in self._tools:
            raise ConfigurationError(
                f"Tool already registered: {config.tool_id}", field="tool_id", value=config.tool_id
            )

        self._tools[config.tool_id] = config
        self._handlers[config.tool_id] = handler
        logger.info(f"Registered tool: {config.tool_id} ({config.name})")

    def get_tool(self, tool_id: str) -> ToolConfig:
        """Get tool configuration."""
        if tool_id not in self._tools:
            raise ResourceNotFoundError(f"Tool not found: {tool_id}")

        config = self._tools[tool_id]
        if not config.enabled:
            raise ValidationError(f"Tool is disabled: {tool_id}")

        return config

    async def execute(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        trace_id: UUID,
        agent_type: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        idempotency_key: Optional[str] = None,
    ) -> ToolExecution:
        """
        Execute tool with full security enforcement.

        Flow:
        1. Validate tool exists and enabled
        2. Check idempotency (prevent duplicate execution)
        3. Check agent is allowed to use tool
        4. Check actor has required permissions (RBAC)
        5. Check policy allows execution
        6. Evaluate risk level
        7. Request approval if needed (high risk)
        8. Check rate limits
        9. Execute tool
        10. Audit execution

        Fail Closed: Any check failure → DENY
        """
        # Check idempotency
        if idempotency_key and idempotency_key in self._executions:
            logger.info(f"Tool execution deduplicated: {tool_id} (key={idempotency_key})")
            return self._executions[idempotency_key]

        # Get tool config
        try:
            config = self.get_tool(tool_id)
        except (ResourceNotFoundError, ValidationError) as e:
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_denied",
                    resource_type="tool",
                    status="denied",
                    user_id=actor_id,
                    details={
                        "reason": "unknown_or_disabled_tool",
                        "tool_id": tool_id,
                        "trace_id": str(trace_id),
                    },
                )
            execution = ToolExecution(
                execution_id=uuid4(),
                tool_id=tool_id,
                agent_type=agent_type,
                actor_id=actor_id,
                trace_id=trace_id,
                status=ToolStatus.DENIED,
                parameters=parameters,
                error=str(e),
                idempotency_key=idempotency_key,
            )
            if idempotency_key:
                self._executions[idempotency_key] = execution
            return execution

        # Check agent is allowed
        if (
            agent_type
            and "*" not in config.allowed_agents
            and agent_type not in config.allowed_agents
        ):
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_denied",
                    resource_type="tool",
                    status="denied",
                    user_id=actor_id,
                    details={
                        "reason": "agent_not_allowed",
                        "tool_id": tool_id,
                        "agent_type": agent_type,
                        "trace_id": str(trace_id),
                    },
                )
            execution = ToolExecution(
                execution_id=uuid4(),
                tool_id=tool_id,
                agent_type=agent_type,
                actor_id=actor_id,
                trace_id=trace_id,
                status=ToolStatus.DENIED,
                parameters=parameters,
                error=f"Agent {agent_type} not allowed to use tool {tool_id}",
                idempotency_key=idempotency_key,
            )
            if idempotency_key:
                self._executions[idempotency_key] = execution
            return execution

        # Check RBAC permissions via RBACService
        if config.required_permissions and self._rbac_service:
            for perm_str in config.required_permissions:
                from src.identity.rbac import Permission
                perm_enum = perm_str if isinstance(perm_str, Permission) else Permission(perm_str)
                has_perm = await self._rbac_service.check_permission_by_id(actor_id, perm_enum)
                if not has_perm:
                    if self._session:
                        await AuditService.log(
                            session=self._session,
                            action="tool_execution_denied",
                            resource_type="tool",
                            status="denied",
                            user_id=actor_id,
                            details={
                                "reason": "permission_denied",
                                "tool_id": tool_id,
                                "required_permission": perm,
                                "trace_id": str(trace_id),
                            },
                        )
                    execution = ToolExecution(
                        execution_id=uuid4(),
                        tool_id=tool_id,
                        agent_type=agent_type,
                        actor_id=actor_id,
                        trace_id=trace_id,
                        status=ToolStatus.DENIED,
                        parameters=parameters,
                        error=f"Permission denied: {perm}",
                        idempotency_key=idempotency_key,
                    )
                    if idempotency_key:
                        self._executions[idempotency_key] = execution
                    return execution

        # Check policy
        policy_decision = await self._policy_engine.evaluate(
            resource_type="tool",
            resource_id=tool_id,
            action="execute",
            actor_id=actor_id,
            context={"agent_type": agent_type, "parameters": parameters, "trace_id": str(trace_id)},
        )

        if policy_decision.action != PolicyAction.ALLOW:
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_denied",
                    resource_type="tool",
                    status="denied",
                    user_id=actor_id,
                    details={
                        "reason": "policy_denied",
                        "tool_id": tool_id,
                        "policy_decision": policy_decision.action.value,
                        "policy_reason": policy_decision.reason,
                        "trace_id": str(trace_id),
                    },
                )
            execution = ToolExecution(
                execution_id=uuid4(),
                tool_id=tool_id,
                agent_type=agent_type,
                actor_id=actor_id,
                trace_id=trace_id,
                status=ToolStatus.DENIED,
                parameters=parameters,
                error=f"Policy denied: {policy_decision.reason}",
                idempotency_key=idempotency_key,
            )
            if idempotency_key:
                self._executions[idempotency_key] = execution
            return execution

        # Evaluate risk
        risk_level = config.risk_level

        # Request approval if needed — real persistence flow
        approval_id = None
        if config.requires_approval and self._session:
            # 1. Create persistence approval request via ApprovalService
            # We construct a minimal User-like object for the requester
            from src.identity.models import User
            requester_mock = User(id=int(actor_id) if actor_id and str(actor_id).isdigit() else 0)
            approval_request = await self._approval_service.create_request(
                requester=requester_mock,
                request_type="tool_execution",
                target_resource="tool",
                target_action="execute",
                target_id=tool_id,
                payload={
                    "tool_id": tool_id,
                    "agent_type": agent_type,
                    "parameters": parameters,
                    "trace_id": str(trace_id),
                },
                reason=f"Execute tool: {config.name}",
                context={"risk_level": risk_level.value, "tool_category": config.category.value},
            )

            # 2. Check if auto-approved (low risk) or needs manual approval
            is_auto_approved = await self._approval_service.check_auto_approval(
                requester=requester_mock,
                request_type="tool_execution",
                target_resource="tool",
                target_action="execute",
                context={"risk_level": risk_level.value},
            )

            if is_auto_approved:
                # Auto-approve: execute immediately
                approval_request.status = ApprovalStatus.APPROVED
                approval_request.approver_id = 0  # system
                approval_request.reviewed_at = datetime.now(UTC)
                await self._session.commit()
                approval_id = str(approval_request.id)
                logger.info(
                    f"Tool {tool_id} auto-approved (low risk), approval_id={approval_request.id}"
                )
                await AuditService.log(
                    session=self._session,
                    action="tool_approval_auto",
                    resource_type="tool",
                    status="approved",
                    user_id=actor_id,
                    details={
                        "tool_id": tool_id,
                        "approval_id": approval_request.id,
                        "trace_id": str(trace_id),
                        "risk_level": risk_level.value,
                    },
                )
            else:
                # Manual approval required: return DENIED with approval_id
                approval_id = str(approval_request.id)
                logger.warning(
                    f"Tool {tool_id} requires manual approval, approval_id={approval_request.id}"
                )
                await AuditService.log(
                    session=self._session,
                    action="tool_approval_required",
                    resource_type="tool",
                    status="pending",
                    user_id=actor_id,
                    details={
                        "tool_id": tool_id,
                        "approval_id": approval_request.id,
                        "risk_level": risk_level.value,
                        "trace_id": str(trace_id),
                    },
                )
                execution = ToolExecution(
                    execution_id=uuid4(),
                    tool_id=tool_id,
                    agent_type=agent_type,
                    actor_id=actor_id,
                    trace_id=trace_id,
                    status=ToolStatus.PENDING,
                    parameters=parameters,
                    approval_id=approval_id,
                    risk_level=risk_level,
                    error=f"Tool requires manual approval. Approval request ID: {approval_request.id}",
                    idempotency_key=idempotency_key,
                )
                if idempotency_key:
                    self._executions[idempotency_key] = execution
                return execution
        elif config.requires_approval and not self._session:
            logger.warning(f"Tool {tool_id} requires approval but no session available - denying")
            execution = ToolExecution(
                execution_id=uuid4(),
                tool_id=tool_id,
                agent_type=agent_type,
                actor_id=actor_id,
                trace_id=trace_id,
                status=ToolStatus.DENIED,
                parameters=parameters,
                error="Approval required but database session unavailable",
                idempotency_key=idempotency_key,
            )
            if idempotency_key:
                self._executions[idempotency_key] = execution
            return execution

        # Check rate limits
        if config.rate_limit_per_hour:
            rate_key = f"{tool_id}:{actor_id or 'anonymous'}"
            now = datetime.now(UTC)

            if rate_key not in self._rate_limits:
                self._rate_limits[rate_key] = []

            # Remove old entries
            self._rate_limits[rate_key] = [
                ts for ts in self._rate_limits[rate_key] if (now - ts).total_seconds() < 3600
            ]

            if len(self._rate_limits[rate_key]) >= config.rate_limit_per_hour:
                if self._session:
                    await AuditService.log(
                        session=self._session,
                        action="tool_execution_denied",
                        resource_type="tool",
                        status="denied",
                        user_id=actor_id,
                        details={
                            "reason": "rate_limit_exceeded",
                            "tool_id": tool_id,
                            "limit": config.rate_limit_per_hour,
                            "trace_id": str(trace_id),
                        },
                    )
                execution = ToolExecution(
                    execution_id=uuid4(),
                    tool_id=tool_id,
                    agent_type=agent_type,
                    actor_id=actor_id,
                    trace_id=trace_id,
                    status=ToolStatus.DENIED,
                    parameters=parameters,
                    error=f"Rate limit exceeded: {config.rate_limit_per_hour}/hour",
                    risk_level=risk_level,
                    idempotency_key=idempotency_key,
                )
                if idempotency_key:
                    self._executions[idempotency_key] = execution
                return execution

            self._rate_limits[rate_key].append(now)

        # Create execution record
        execution = ToolExecution(
            execution_id=uuid4(),
            tool_id=tool_id,
            agent_type=agent_type,
            actor_id=actor_id,
            trace_id=trace_id,
            status=ToolStatus.EXECUTING,
            parameters=parameters,
            approval_id=approval_id,
            risk_level=risk_level,
            idempotency_key=idempotency_key,
        )

        if idempotency_key:
            self._executions[idempotency_key] = execution

        try:
            # Execute tool handler
            handler = self._handlers[tool_id]
            result = await handler(parameters)

            # Update execution
            execution.status = ToolStatus.COMPLETED
            execution.result = result
            execution.completed_at = datetime.now(UTC)

            # Audit success
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_success",
                    resource_type="tool",
                    status="success",
                    user_id=actor_id,
                    resource_id=tool_id,
                    details={
                        "tool_id": tool_id,
                        "agent_type": agent_type,
                        "execution_id": str(execution.execution_id),
                        "trace_id": str(trace_id),
                        "risk_level": risk_level.value if hasattr(risk_level, 'value') else str(risk_level),
                    },
                )

            logger.info(
                f"Tool executed successfully: {tool_id} (execution_id={execution.execution_id})"
            )

        except Exception as e:
            # Update execution with error
            execution.status = ToolStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(UTC)

            # Audit failure
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_failure",
                    resource_type="tool",
                    status="failure",
                    user_id=actor_id,
                    resource_id=tool_id,
                    details={
                        "tool_id": tool_id,
                        "agent_type": agent_type,
                        "execution_id": str(execution.execution_id),
                        "trace_id": str(trace_id),
                        "error": str(e),
                    },
                )

            logger.error(
                f"Tool execution failed: {tool_id} (execution_id={execution.execution_id}): {e}"
            )

        return execution

    def list_tools(
        self, category: Optional[ToolCategory] = None, enabled_only: bool = True
    ) -> List[ToolConfig]:
        """List registered tools."""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if enabled_only:
            tools = [t for t in tools if t.enabled]

        return tools

    def get_execution(self, execution_id: UUID) -> Optional[ToolExecution]:
        """Get tool execution by ID."""
        for execution in self._executions.values():
            if execution.execution_id == execution_id:
                return execution
        return None

    async def execute_approved(
        self,
        execution_id: UUID,
        approval_id: str,
        trace_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> ToolExecution:
        """
        Execute a tool after it has been approved.

        This is called after the approval request has been approved by a human.
        Verifies the approval is still valid, then executes the tool.

        Args:
            execution_id: The execution ID from the pending execution
            approval_id: The approval request ID that was approved
            trace_id: Original trace ID for auditing
            actor_id: User/agent who approved the execution

        Returns:
            ToolExecution with execution result
        """
        # Find the pending execution
        execution = None
        for exec_key, stored_exec in self._executions.items():
            if stored_exec.execution_id == execution_id:
                execution = stored_exec
                break

        if not execution:
            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_approval_execution_failed",
                    resource_type="tool",
                    status="failed",
                    user_id=actor_id,
                    details={
                        "reason": "execution_not_found",
                        "execution_id": str(execution_id),
                        "trace_id": str(trace_id),
                    },
                )
            raise ResourceNotFoundError(f"Execution not found: {execution_id}")

        # Verify approval is valid
        if self._session:
            is_approved = await self._approval_service.is_approved(int(approval_id))
            if not is_approved:
                execution.status = ToolStatus.DENIED
                execution.error = "Approval was not granted or has expired"
                execution.completed_at = datetime.now(UTC)
                if self._session:
                    await AuditService.log(
                        session=self._session,
                        action="tool_execution_denied",
                        resource_type="tool",
                        status="denied",
                        user_id=actor_id,
                        resource_id=execution.tool_id,
                        details={
                            "reason": "approval_not_granted",
                            "execution_id": str(execution_id),
                            "approval_id": approval_id,
                            "trace_id": str(trace_id),
                        },
                    )
                return execution

        # Execute the tool
        execution.status = ToolStatus.EXECUTING
        execution.started_at = datetime.now(UTC)

        try:
            handler = self._handlers[execution.tool_id]
            result = await handler(execution.parameters)

            execution.status = ToolStatus.COMPLETED
            execution.result = result
            execution.completed_at = datetime.now(UTC)

            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_success",
                    resource_type="tool",
                    status="success",
                    user_id=actor_id,
                    resource_id=execution.tool_id,
                    details={
                        "tool_id": execution.tool_id,
                        "execution_id": str(execution_id),
                        "approval_id": approval_id,
                        "trace_id": str(trace_id),
                    },
                )

            logger.info(
                f"Approved tool executed: {execution.tool_id} (execution_id={execution_id})"
            )

        except Exception as e:
            execution.status = ToolStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(UTC)

            if self._session:
                await AuditService.log(
                    session=self._session,
                    action="tool_execution_failure",
                    resource_type="tool",
                    status="failure",
                    user_id=actor_id,
                    resource_id=execution.tool_id,
                    details={
                        "tool_id": execution.tool_id,
                        "execution_id": str(execution_id),
                        "approval_id": approval_id,
                        "trace_id": str(trace_id),
                        "error": str(e),
                    },
                )

        return execution
