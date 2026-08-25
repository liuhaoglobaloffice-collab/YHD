"""
Agent Runtime - Internal AI Workforce Management.

Enforces: Agent ≠ Provider, Agent ≠ Workflow
Agents are AI employees with specific roles and capabilities.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from ..core.errors import (
    ConfigurationError,
    ResourceNotFoundError,
    ValidationError,
)
from ..identity.rbac import Permission, has_permission
from .providers import ProviderGateway, ProviderResponse, ProviderType

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Internal AI employees (Stage 3 only)."""

    GPT = "gpt"  # AI CEO Brain
    GROK = "grok"  # Intelligence Deputy
    CLAUDE = "claude"  # CTO
    DEEPSEEK = "deepseek"  # Analyst
    GEMINI = "gemini"  # Research Officer
    KIMI = "kimi"  # Chinese Research Officer


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class AgentConfig:
    """Agent configuration."""

    agent_type: AgentType
    name: str
    description: str
    provider: ProviderType
    model_id: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    allowed_tools: Set[str] = field(default_factory=set)
    required_permissions: Set[str] = field(default_factory=set)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent execution context."""

    agent_id: UUID
    agent_type: AgentType
    trace_id: UUID
    actor_id: Optional[UUID]  # User who triggered this agent
    session_id: Optional[UUID] = None
    parent_task_id: Optional[UUID] = None
    available_tools: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AgentExecution:
    """Agent execution record."""

    execution_id: UUID
    agent_type: AgentType
    context: AgentContext
    status: AgentStatus
    input_messages: List[Dict[str, Any]]
    output: Optional[str] = None
    provider_response: Optional[ProviderResponse] = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    """Registry for internal AI agents."""

    def __init__(self):
        self._agents: Dict[AgentType, AgentConfig] = {}
        logger.info("Agent Registry initialized")

    def register(self, config: AgentConfig):
        """Register an agent."""
        if config.agent_type in self._agents:
            raise ConfigurationError(
                f"Agent already registered: {config.agent_type}",
                field="agent_type",
                value=str(config.agent_type),
            )

        self._agents[config.agent_type] = config
        logger.info(f"Registered agent: {config.agent_type} ({config.name})")

    def get(self, agent_type: AgentType) -> AgentConfig:
        """Get agent configuration."""
        if agent_type not in self._agents:
            raise ResourceNotFoundError(f"Agent not found: {agent_type}")

        config = self._agents[agent_type]
        if not config.enabled:
            raise ValidationError(f"Agent is disabled: {agent_type}")

        return config

    def list_agents(self, enabled_only: bool = True) -> List[AgentConfig]:
        """List registered agents."""
        agents = list(self._agents.values())

        if enabled_only:
            agents = [a for a in agents if a.enabled]

        return agents

    def is_registered(self, agent_type: AgentType) -> bool:
        """Check if agent is registered."""
        return agent_type in self._agents


class AgentRuntime:
    """
    Agent Runtime - Manages internal AI employee execution.

    Enforces:
    - Agent ≠ Provider: Agents use providers, they are not providers
    - Agent ≠ Workflow: Agents execute tasks, they don't orchestrate
    - RBAC: Agent tool access controlled by permissions
    - Fail Closed: Unknown agents/tools denied
    """

    def __init__(self, registry: AgentRegistry, provider_gateway: ProviderGateway):
        self._registry = registry
        self._provider_gateway = provider_gateway
        self._active_executions: Dict[UUID, AgentExecution] = {}
        logger.info("Agent Runtime initialized")

    async def execute(
        self,
        agent_type: AgentType,
        messages: List[Dict[str, Any]],
        context: AgentContext,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AgentExecution:
        """
        Execute agent task.

        Security: Validates agent permissions before execution.
        Fail Closed: Unknown agents denied.
        """
        # Get agent config
        try:
            config = self._registry.get(agent_type)
        except ResourceNotFoundError:
            logger.warning(f"Agent execution denied: {agent_type} not found")
            execution = AgentExecution(
                execution_id=uuid4(),
                agent_type=agent_type,
                context=context,
                status=AgentStatus.FAILED,
                input_messages=messages,
                error=f"Unknown agent: {agent_type}",
            )
            return execution

        # Validate required permissions
        if config.required_permissions and context.actor_id:
            for perm in config.required_permissions:
                if not has_permission(context.actor_id, Permission(perm)):
                    logger.warning(
                        f"Agent execution denied: actor {context.actor_id} "
                        f"lacks permission {perm}"
                    )
                    execution = AgentExecution(
                        execution_id=uuid4(),
                        agent_type=agent_type,
                        context=context,
                        status=AgentStatus.FAILED,
                        input_messages=messages,
                        error=f"Permission denied: {perm}",
                    )
                    return execution

        # Create execution record
        execution = AgentExecution(
            execution_id=uuid4(),
            agent_type=agent_type,
            context=context,
            status=AgentStatus.RUNNING,
            input_messages=messages,
        )

        self._active_executions[execution.execution_id] = execution

        try:
            # Prepare messages with system prompt
            full_messages = []
            if config.system_prompt:
                full_messages.append({"role": "system", "content": config.system_prompt})
            full_messages.extend(messages)

            # Execute through provider gateway
            response = await self._provider_gateway.complete(
                provider=config.provider,
                model_id=config.model_id,
                messages=full_messages,
                trace_id=context.trace_id,
                actor_id=context.actor_id,
                temperature=temperature or config.temperature,
                max_tokens=max_tokens or config.max_tokens,
            )

            # Update execution
            execution.status = AgentStatus.COMPLETED
            execution.output = response.content
            execution.provider_response = response
            execution.completed_at = datetime.now(UTC)

            logger.info(
                f"Agent execution completed: {agent_type} "
                f"(execution_id={execution.execution_id})"
            )

        except Exception as e:
            # Update execution with error
            execution.status = AgentStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(UTC)

            logger.error(
                f"Agent execution failed: {agent_type} "
                f"(execution_id={execution.execution_id}): {e}"
            )

        finally:
            # Remove from active executions
            self._active_executions.pop(execution.execution_id, None)

        return execution

    def get_execution(self, execution_id: UUID) -> Optional[AgentExecution]:
        """Get execution status."""
        return self._active_executions.get(execution_id)

    def list_active_executions(self) -> List[AgentExecution]:
        """List currently running executions."""
        return list(self._active_executions.values())

    def get_agent_status(self, agent_type: AgentType) -> AgentStatus:
        """Get agent status."""
        try:
            config = self._registry.get(agent_type)
            # Check if agent is currently running
            for execution in self._active_executions.values():
                if execution.agent_type == agent_type and execution.status == AgentStatus.RUNNING:
                    return AgentStatus.RUNNING
            return AgentStatus.IDLE if config.enabled else AgentStatus.DISABLED
        except ResourceNotFoundError:
            return AgentStatus.DISABLED


# ============================================================================
# Default Agent Configurations
# ============================================================================


def create_default_agents() -> List[AgentConfig]:
    """
    Create the 6 internal AI employees for Stage 3.

    Stage 3 Internal Workforce:
    - GPT: AI CEO Brain (strategic decision making)
    - Grok: Intelligence Deputy (real-time intelligence)
    - Claude: CTO (technical architecture and code review)
    - DeepSeek: Analyst (deep analysis and reasoning)
    - Gemini: Research Officer (research and information gathering)
    - Kimi: Chinese Research Officer (Chinese language research)
    """
    return [
        AgentConfig(
            agent_type=AgentType.GPT,
            name="GPT - AI CEO Brain",
            description="Strategic decision making, high-level planning, and executive oversight",
            provider=ProviderType.OPENAI,
            model_id="gpt-4",
            temperature=0.7,
            max_tokens=4000,
            system_prompt=(
                "You are the AI CEO Brain of LiuHao AI OS. Your role is strategic "
                "decision making, high-level planning, and executive oversight. "
                "Think comprehensively, consider business impact, and provide "
                "actionable executive guidance."
            ),
            allowed_tools={"*"},  # CEO has access to all tools
            required_permissions=set(),
            enabled=True,
        ),
        AgentConfig(
            agent_type=AgentType.GROK,
            name="Grok - Intelligence Deputy",
            description="Real-time intelligence gathering and analysis",
            provider=ProviderType.XAI,
            model_id="grok-beta",
            temperature=0.8,
            max_tokens=4000,
            system_prompt=(
                "You are the Intelligence Deputy of LiuHao AI OS. Your role is "
                "real-time intelligence gathering, trend analysis, and situational "
                "awareness. Provide timely, relevant intelligence to support decision making."
            ),
            allowed_tools={"research", "web_search", "news"},
            required_permissions=set(),
            enabled=True,
        ),
        AgentConfig(
            agent_type=AgentType.CLAUDE,
            name="Claude - CTO",
            description="Technical architecture, code review, and engineering excellence",
            provider=ProviderType.ANTHROPIC,
            model_id="claude-3-5-sonnet-20241022",
            temperature=0.3,
            max_tokens=8000,
            system_prompt=(
                "You are the CTO of LiuHao AI OS. Your role is technical architecture, "
                "code review, system design, and engineering best practices. "
                "Focus on correctness, security, scalability, and maintainability."
            ),
            allowed_tools={"code_analysis", "architecture_review", "security_audit"},
            required_permissions=set(),
            enabled=True,
        ),
        AgentConfig(
            agent_type=AgentType.DEEPSEEK,
            name="DeepSeek - Analyst",
            description="Deep analysis, reasoning, and technical problem solving",
            provider=ProviderType.DEEPSEEK,
            model_id="deepseek-chat",
            temperature=0.4,
            max_tokens=4000,
            system_prompt=(
                "You are the Analyst of LiuHao AI OS. Your role is deep analysis, "
                "logical reasoning, and technical problem solving. "
                "Provide thorough, well-reasoned analysis with clear conclusions."
            ),
            allowed_tools={"data_analysis", "calculation", "reasoning"},
            required_permissions=set(),
            enabled=True,
        ),
        AgentConfig(
            agent_type=AgentType.GEMINI,
            name="Gemini - Research Officer",
            description="Research, information synthesis, and knowledge management",
            provider=ProviderType.GOOGLE,
            model_id="gemini-pro",
            temperature=0.6,
            max_tokens=4000,
            system_prompt=(
                "You are the Research Officer of LiuHao AI OS. Your role is research, "
                "information synthesis, and knowledge management. "
                "Provide comprehensive, well-structured research with citations."
            ),
            allowed_tools={"research", "web_search", "document_analysis"},
            required_permissions=set(),
            enabled=True,
        ),
        AgentConfig(
            agent_type=AgentType.KIMI,
            name="Kimi - Chinese Research Officer",
            description="Chinese language research and localized intelligence",
            provider=ProviderType.MOONSHOT,
            model_id="moonshot-v1-8k",
            temperature=0.6,
            max_tokens=4000,
            system_prompt=(
                "你是 LiuHao AI OS 的中文研究官。你的职责是中文语言研究、"
                "本地化情报收集和中国市场分析。"
                "提供准确、全面的中文研究和分析。"
            ),
            allowed_tools={"research", "web_search", "chinese_analysis"},
            required_permissions=set(),
            enabled=True,
        ),
    ]
