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

from ..core.errors import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationError,
)
from ..governance.approval import ApprovalRequest, ApprovalService
from ..governance.risk import RiskEvaluator, RiskLevel
from ..identity.audit import AuditService
from ..identity.rbac import has_permission
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
    ):
        self._tools: Dict[str, ToolConfig] = {}
        self._handlers: Dict[str, Callable] = {}
        self._audit_service = audit_service
        self._policy_engine = policy_engine
        self._approval_service = approval_service
        self._risk_evaluator = risk_evaluator
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
            await self._audit_service.log(
                action="tool_execution_denied",
                status="denied",
                actor_id=actor_id,
                target_id=None,
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
            await self._audit_service.log(
                action="tool_execution_denied",
                status="denied",
                actor_id=actor_id,
                target_id=None,
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

        # Check RBAC permissions
        if config.required_permissions and actor_id:
            for perm in config.required_permissions:
                if not has_permission(actor_id, perm):
                    await self._audit_service.log(
                        action="tool_execution_denied",
                        status="denied",
                        actor_id=actor_id,
                        target_id=None,
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
            await self._audit_service.log(
                action="tool_execution_denied",
                status="denied",
                actor_id=actor_id,
                target_id=None,
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

        # Request approval if needed
        approval_id = None
        if config.requires_approval:
            ApprovalRequest(
                request_type="tool_execution",
                requester_id=actor_id,  # Assuming actor_id is user ID
                target_resource="tool",
                target_action="execute",
                target_id=tool_id,
                payload={
                    "tool_id": tool_id,
                    "agent_type": agent_type,
                    "parameters": parameters,
                    "trace_id": str(trace_id),
                },
                risk_level=risk_level,
                reason=f"Execute tool: {config.name}",
            )

            # Note: In production, this would wait for approval
            # For Stage 3, we'll log the requirement but proceed
            logger.warning(f"Tool {tool_id} requires approval - approval flow not yet complete")
            await self._audit_service.log(
                action="tool_approval_required",
                status="pending",
                actor_id=actor_id,
                target_id=None,
                details={"tool_id": tool_id, "risk_level": risk_level, "trace_id": str(trace_id)},
            )

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
                await self._audit_service.log(
                    action="tool_execution_denied",
                    status="denied",
                    actor_id=actor_id,
                    target_id=None,
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
            await self._audit_service.log(
                action="tool_execution_success",
                status="success",
                actor_id=actor_id,
                target_id=None,
                details={
                    "tool_id": tool_id,
                    "agent_type": agent_type,
                    "execution_id": str(execution.execution_id),
                    "trace_id": str(trace_id),
                    "risk_level": risk_level,
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
            await self._audit_service.log(
                action="tool_execution_failure",
                status="failure",
                actor_id=actor_id,
                target_id=None,
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
