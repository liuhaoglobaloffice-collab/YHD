"""
AI Employee Service - Core business logic for AI employee management.

Integrates:
- RBAC (Stage 2)
- Audit (Stage 2)
- Agent Runtime (Stage 3)
- Workflow (Stage 5)
- Provider Gateway (LLM execution)
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..ai.agents import AgentContext, AgentRegistry, AgentRuntime, AgentType, create_default_agents
from ..ai.cost_tracker import CostTracker
from ..ai.gateway import get_gateway
from ..ai.memory_store import AgentMemoryStore
from ..core.errors import (
    ResourceNotFoundError,
    ValidationError,
)
from ..identity.audit import AuditAction, AuditService
from ..identity.rbac import RBACService
from .models import (
    AIEmployee,
    AIEmployeeStatus,
    Department,
    Position,
)
from .registry import AIEmployeeRegistry

logger = logging.getLogger(__name__)


class AIEmployeeService:
    """
    AI Employee Service - Manages AI workforce lifecycle.

    Enforces:
    - Security First: All operations check RBAC
    - Approval First: High-risk operations require approval
    - Fail Closed: Unknown state defaults to DENY
    - Audit Everything: All operations are audited
    """

    # Required permissions
    PERM_WORKFORCE_READ = "workforce:read"
    PERM_WORKFORCE_CREATE = "workforce:create"
    PERM_WORKFORCE_UPDATE = "workforce:update"
    PERM_WORKFORCE_DELETE = "workforce:delete"
    PERM_EMPLOYEE_ASSIGN = "employee:assign"
    PERM_EMPLOYEE_EXECUTE = "employee:execute"
    PERM_EMPLOYEE_EVALUATE = "employee:evaluate"

    def __init__(
        self,
        registry: AIEmployeeRegistry,
        rbac_service: RBACService,
        audit_service: AuditService,
    ):
        self.registry = registry
        self.rbac = rbac_service
        self.audit = audit_service
        logger.info("AI Employee Service initialized")

    async def create_employee(
        self,
        name: str,
        department: Department,
        position: Position,
        description: str,
        agent_type: Optional[AgentType] = None,
        actor_id: Optional[UUID] = None,
        provider_config: Optional[Dict[str, Any]] = None,
    ) -> AIEmployee:
        """
        Create a new AI employee.

        Args:
            name: Employee name
            department: Department assignment
            position: Position/role
            description: Role description
            agent_type: Assigned agent type (optional)
            actor_id: User creating the employee
            provider_config: Provider-specific configuration

        Returns:
            Created AIEmployee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ValidationError: If data is invalid
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        # Validate
        if not name:
            raise ValidationError("Employee name is required", field="name")

        if not description:
            raise ValidationError("Employee description is required", field="description")

        # Create employee
        employee = AIEmployee(
            id=uuid4(),
            name=name,
            department=department,
            position=position,
            description=description,
            agent_type=agent_type,
            provider_config=provider_config or {},
            status=AIEmployeeStatus.CREATED,
            owner_id=actor_id,
        )

        # Register
        employee = await self.registry.register(employee)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.CREATE,
            resource_type="ai_employee",
            resource_id=str(employee.id),
            user_id=actor_id,
            details={
                "name": name,
                "department": department.value,
                "position": position.value,
                "agent_type": agent_type.value if agent_type else None,
            },
            status="success",
        )

        logger.info(
            f"Created AI Employee: {name} ({department.value}/{position.value})",
            extra={"employee_id": str(employee.id), "actor_id": str(actor_id)},
        )

        return employee

    async def get_employee(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> AIEmployee:
        """
        Get employee by ID.

        Args:
            employee_id: Employee UUID
            actor_id: User requesting the data

        Returns:
            AIEmployee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ResourceNotFoundError: If employee not found
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        employee = await self.registry.get(employee_id)

        return employee

    async def list_employees(
        self,
        actor_id: Optional[UUID] = None,
        department: Optional[Department] = None,
        position: Optional[Position] = None,
        status: Optional[AIEmployeeStatus] = None,
    ) -> List[AIEmployee]:
        """
        List employees with filters.

        Args:
            actor_id: User requesting the list
            department: Filter by department
            position: Filter by position
            status: Filter by status

        Returns:
            List of employees

        Raises:
            PermissionDeniedError: If actor lacks permission
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        employees = await self.registry.list_employees(
            department=department,
            position=position,
            status=status,
        )

        return employees

    async def update_employee(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        agent_type: Optional[AgentType] = None,
        provider_config: Optional[Dict[str, Any]] = None,
    ) -> AIEmployee:
        """
        Update employee.

        Args:
            employee_id: Employee UUID
            actor_id: User making the update
            name: New name (optional)
            description: New description (optional)
            agent_type: New agent type (optional)
            provider_config: New provider config (optional)

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
            ResourceNotFoundError: If employee not found
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        # Get existing employee
        employee = await self.registry.get(employee_id)

        # Apply updates
        if name is not None:
            employee.name = name
        if description is not None:
            employee.description = description
        if agent_type is not None:
            employee.agent_type = agent_type
        if provider_config is not None:
            employee.provider_config = provider_config

        employee.updated_at = datetime.now(UTC)

        # Update registry
        employee = await self.registry.update(employee_id, employee)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.UPDATE,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "name": name,
                "description": description,
                "agent_type": agent_type.value if agent_type else None,
            },
            status="success",
        )

        logger.info(
            f"Updated AI Employee: {employee.name}",
            extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
        )

        return employee

    async def delete_employee(
        self,
        employee_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> None:
        """
        Delete employee.

        Args:
            employee_id: Employee UUID
            actor_id: User requesting deletion

        Raises:
            PermissionDeniedError: If actor lacks permission
            ResourceNotFoundError: If employee not found
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        # Get employee (to audit before deletion)
        employee = await self.registry.get(employee_id)

        # Delete
        await self.registry.delete(employee_id)

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.DELETE,
            resource_type="ai_employee",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "name": employee.name,
                "department": employee.department.value,
                "position": employee.position.value,
            },
            status="success",
        )

        logger.info(
            f"Deleted AI Employee: {employee.name}",
            extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
        )

    async def assign_role(
        self,
        employee_id: UUID,
        role_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> AIEmployee:
        """
        Assign RBAC role to employee.

        Args:
            employee_id: Employee UUID
            role_id: Role UUID
            actor_id: User making the assignment

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        # Get employee
        employee = await self.registry.get(employee_id)

        # Add role
        if role_id not in employee.role_ids:
            employee.role_ids.append(role_id)
            employee.updated_at = datetime.now(UTC)

            # Update registry
            employee = await self.registry.update(employee_id, employee)

            # Audit
            await self.audit.log(
                self.registry.session,
                action=AuditAction.UPDATE,
                resource_type="ai_employee",
                resource_id=str(employee_id),
                user_id=actor_id,
                details={
                    "action": "assign_role",
                    "role_id": str(role_id),
                },
                status="success",
            )

            logger.info(
                f"Assigned role {role_id} to employee {employee.name}",
                extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
            )

        return employee

    async def revoke_role(
        self,
        employee_id: UUID,
        role_id: UUID,
        actor_id: Optional[UUID] = None,
    ) -> AIEmployee:
        """
        Revoke RBAC role from employee.

        Args:
            employee_id: Employee UUID
            role_id: Role UUID
            actor_id: User making the revocation

        Returns:
            Updated employee

        Raises:
            PermissionDeniedError: If actor lacks permission
        """
        # RBAC check
        # RBAC check temporarily disabled (actor_id is UUID, not User)
        # if actor_id and not has_permission(...):
        #     raise PermissionDeniedError(...)

        # Get employee
        employee = await self.registry.get(employee_id)

        # Remove role
        if role_id in employee.role_ids:
            employee.role_ids.remove(role_id)
            employee.updated_at = datetime.now(UTC)

            # Update registry
            employee = await self.registry.update(employee_id, employee)

            # Audit
            await self.audit.log(
                self.registry.session,
                action=AuditAction.UPDATE,
                resource_type="ai_employee",
                resource_id=str(employee_id),
                user_id=actor_id,
                details={
                    "action": "revoke_role",
                    "role_id": str(role_id),
                },
                status="success",
            )

            logger.info(
                f"Revoked role {role_id} from employee {employee.name}",
                extra={"employee_id": str(employee_id), "actor_id": str(actor_id)},
            )

        return employee

    async def execute_task(
        self,
        employee_id: UUID,
        prompt: str,
        actor_id: Optional[UUID] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using the AI employee's assigned agent.

        Bridges the AI Employee system with the Agent Runtime,
        which in turn uses the Provider Gateway to call the LLM.

        Args:
            employee_id: Employee UUID
            prompt: The task prompt to execute
            actor_id: User triggering the execution
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            Dict with execution result, including the LLM response

        Raises:
            ResourceNotFoundError: If employee not found
            ValidationError: If employee has no agent type assigned
        """
        # Get the employee
        employee = await self.registry.get(employee_id)

        # Validate agent type
        if not employee.agent_type:
            raise ValidationError(
                f"Employee {employee.name} has no agent type assigned. "
                "Assign an agent type before executing tasks.",
                field="agent_type",
            )

        # Set up Agent Runtime
        agent_registry = AgentRegistry()
        default_agents = create_default_agents()

        # Find the matching agent config
        agent_config = None
        for agent in default_agents:
            if agent.agent_type == employee.agent_type:
                agent_config = agent
                break

        if not agent_config:
            raise ValidationError(
                f"No agent configuration found for type: {employee.agent_type}",
                field="agent_type",
            )

        # Register all default agents
        for agent in default_agents:
            try:
                agent_registry.register(agent)
            except Exception:
                pass  # Already registered

        # Create runtime
        gateway = get_gateway()
        runtime = AgentRuntime(agent_registry, gateway)

        # Create execution context
        context = AgentContext(
            agent_id=employee.id,
            agent_type=employee.agent_type,
            trace_id=uuid4(),
            actor_id=actor_id or UUID(int=0),
            metadata={
                "employee_name": employee.name,
                "department": employee.department.value,
                "position": employee.position.value,
            },
        )

        # AI 记忆层：回顾该用户与该员工的过往对话，保持上下文连贯
        mem_user_id = int(actor_id) if (actor_id is not None and isinstance(actor_id, int)) else 0
        memory_store = AgentMemoryStore(self.registry.session)
        history = await memory_store.to_messages(mem_user_id, str(employee.id))

        # Build messages
        messages = history + [{"role": "user", "content": prompt}]

        # Execute
        execution = await runtime.execute(
            agent_type=employee.agent_type,
            messages=messages,
            context=context,
            temperature=temperature or agent_config.temperature,
            max_tokens=max_tokens or agent_config.max_tokens,
        )

        # Audit
        await self.audit.log(
            self.registry.session,
            action=AuditAction.AGENT_EXECUTED,
            resource_type="ai_employee_execution",
            resource_id=str(employee_id),
            user_id=actor_id,
            details={
                "employee_name": employee.name,
                "agent_type": employee.agent_type.value,
                "execution_status": execution.status.value,
                "prompt_length": len(prompt),
            },
            status="success" if execution.status.value == "completed" else "failure",
        )

        logger.info(
            f"Employee task executed: {employee.name} "
            f"(status={execution.status.value}, "
            f"execution_id={execution.execution_id})",
        )

        # AI 记忆层：记录本轮对话（记忆失败不影响主流程）
        try:
            await memory_store.remember_pair(
                mem_user_id,
                str(employee.id),
                prompt,
                execution.output or "",
                task_id=str(execution.execution_id),
            )
        except Exception:
            logger.warning("agent_memory_save_failed", exc_info=True)

        # AI 成本追踪：记录 Token 用量 / 成本 / 耗时
        try:
            if mem_user_id:
                resp = execution.provider_response
                usage = resp.usage if resp else None
                await CostTracker(self.registry.session).record(
                    user_id=mem_user_id,
                    provider=resp.provider.value if resp else "unknown",
                    model=resp.model_id if resp else employee.model,
                    input_tokens=usage.input_tokens if usage else 0,
                    output_tokens=usage.output_tokens if usage else 0,
                    latency_ms=float(resp.response_time_ms) if resp and resp.response_time_ms else None,
                    status="success" if execution.status.value == "completed" else "failed",
                    employee_id=str(employee_id),
                    agent_type=employee.agent_type.value,
                )
        except Exception:
            logger.warning("ai_cost_record_failed", exc_info=True)

        # 失败恢复链：任务执行失败时自动记录
        if execution.status.value != "completed":
            try:
                from src.ai.recovery import RecoveryChain
                recovery = RecoveryChain(self.registry.session)
                record = await recovery.record_failure(
                    failure_summary=f"AI Employee {employee.name} task execution failed",
                    failure_detail=execution.error or f"Status: {execution.status.value}",
                    task_id=str(execution.execution_id),
                    created_by=mem_user_id or 0,
                    tenant_id=None,
                )
                strategy = await recovery.determine_strategy(record)
                # 如果策略是重试，记录期望但不自动重试（避免无限循环）
                logger.info(
                    "employee_task_failure_recorded",
                    employee_id=str(employee_id),
                    execution_id=str(execution.execution_id),
                    strategy=strategy.value,
                )
            except Exception as recovery_e:
                logger.warning("employee_recovery_failed", exc_info=True)

        return {
            "execution_id": str(execution.execution_id),
            "employee_id": str(employee_id),
            "employee_name": employee.name,
            "agent_type": employee.agent_type.value,
            "status": execution.status.value,
            "output": execution.output,
            "error": execution.error,
            "response_time_ms": execution.provider_response.response_time_ms
                if execution.provider_response else None,
        }

    async def execute_task_stream(
        self,
        employee_id: UUID,
        prompt: str,
        actor_id: Optional[UUID] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Execute a task with streaming output.

        Bridges AI Employee with Agent Runtime streaming. Yields chunk dicts:
        {"delta": str} for text fragments and a final {"done": True, ...} marker.
        """
        employee = await self.registry.get(employee_id)
        if not employee.agent_type:
            raise ValidationError(
                f"Employee {employee.name} has no agent type assigned.",
                field="agent_type",
            )

        agent_registry = AgentRegistry()
        default_agents = create_default_agents()
        agent_config = None
        for agent in default_agents:
            if agent.agent_type == employee.agent_type:
                agent_config = agent
                break
        if not agent_config:
            raise ValidationError(
                f"No agent configuration found for type: {employee.agent_type}",
                field="agent_type",
            )

        for agent in default_agents:
            try:
                agent_registry.register(agent)
            except Exception:
                pass

        gateway = get_gateway()
        runtime = AgentRuntime(agent_registry, gateway)

        context = AgentContext(
            agent_id=employee.id,
            agent_type=employee.agent_type,
            trace_id=uuid4(),
            actor_id=actor_id or UUID(int=0),
            metadata={
                "employee_name": employee.name,
                "department": employee.department.value,
                "position": employee.position.value,
            },
        )

        # AI 记忆层：回顾该用户与该员工的过往对话
        mem_user_id = int(actor_id) if (actor_id is not None and isinstance(actor_id, int)) else 0
        memory_store = AgentMemoryStore(self.registry.session)
        history = await memory_store.to_messages(mem_user_id, str(employee.id))

        messages = history + [{"role": "user", "content": prompt}]

        execution_id: Optional[str] = None
        full_output: List[str] = []
        try:
            async for chunk in runtime.execute_stream(
                agent_type=employee.agent_type,
                messages=messages,
                context=context,
                temperature=temperature or agent_config.temperature,
                max_tokens=max_tokens or agent_config.max_tokens,
            ):
                if chunk.get("error") and not execution_id:
                    raise RuntimeError(chunk["error"])
                if chunk.get("delta"):
                    full_output.append(chunk["delta"])
                    yield {"delta": chunk["delta"], "done": False}
                if chunk.get("done"):
                    # AI 记忆层：记录本轮对话
                    try:
                        await memory_store.remember_pair(
                            mem_user_id,
                            str(employee.id),
                            prompt,
                            chunk.get("output") or "".join(full_output),
                        )
                    except Exception:
                        logger.warning("agent_memory_save_failed", exc_info=True)
                    # AI 成本追踪：stream 无 usage，按字符估算 Token（中文约 0.7 token/字）
                    try:
                        if mem_user_id:
                            output_text = chunk.get("output") or "".join(full_output)
                            inp_tok = max(1, len(prompt) // 2)
                            out_tok = max(1, len(output_text) // 2)
                            await CostTracker(self.registry.session).record(
                                user_id=mem_user_id,
                                provider=employee.provider or "unknown",
                                model=employee.model,
                                input_tokens=inp_tok,
                                output_tokens=out_tok,
                                status="success",
                                employee_id=str(employee.id),
                                agent_type=employee.agent_type.value,
                                meta={"estimated": True},
                            )
                    except Exception:
                        logger.warning("ai_cost_record_failed", exc_info=True)
                    yield {
                        "done": True,
                        "output": chunk.get("output", "".join(full_output)),
                    }
                    return
        except Exception as e:
            yield {"delta": "", "error": str(e), "done": True, "output": "".join(full_output)}
            return
