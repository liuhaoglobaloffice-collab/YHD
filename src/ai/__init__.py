"""
AI Module - Stage 3: AI Brain

Provides:
- Provider Gateway: Unified AI provider abstraction
- Agent Runtime: Internal AI workforce (6 employees)
- AI Orchestrator: Multi-agent task coordination
- Tool Registry: Unified tool management

Enforces:
- Provider ≠ Agent
- Agent ≠ Workflow
- Security First, Approval First, Fail Closed, Audit Everything
"""

from .agents import (
    AgentConfig,
    AgentContext,
    AgentExecution,
    AgentRegistry,
    AgentRuntime,
    AgentStatus,
    AgentType,
    create_default_agents,
)
from .orchestrator import (
    AIOrchestrator,
    ExecutionMode,
    Task,
    TaskPlan,
    TaskPriority,
    TaskResult,
    TaskStatus,
    TaskStep,
)
from .providers import (
    AnthropicProvider,
    BaseProvider,
    DeepSeekProvider,
    GoogleProvider,
    ModelConfig,
    ModelRegistry,
    MoonshotProvider,
    OpenAIProvider,
    ProviderConfig,
    ProviderGateway,
    ProviderMetrics,
    ProviderRequest,
    ProviderResponse,
    ProviderStatus,
    ProviderType,
    TokenUsage,
    XAIProvider,
)
from .tools import (
    ToolCategory,
    ToolConfig,
    ToolExecution,
    ToolRegistry,
    ToolStatus,
)

__all__ = [
    # Providers
    "ProviderType",
    "ProviderStatus",
    "ProviderConfig",
    "ModelConfig",
    "ProviderRequest",
    "ProviderResponse",
    "ProviderMetrics",
    "TokenUsage",
    "BaseProvider",
    "ProviderGateway",
    "ModelRegistry",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "XAIProvider",
    "DeepSeekProvider",
    "MoonshotProvider",
    # Agents
    "AgentType",
    "AgentStatus",
    "AgentConfig",
    "AgentContext",
    "AgentExecution",
    "AgentRegistry",
    "AgentRuntime",
    "create_default_agents",
    # Tools
    "ToolCategory",
    "ToolStatus",
    "ToolConfig",
    "ToolExecution",
    "ToolRegistry",
    # Orchestrator
    "TaskPriority",
    "TaskStatus",
    "ExecutionMode",
    "Task",
    "TaskStep",
    "TaskPlan",
    "TaskResult",
    "AIOrchestrator",
]
