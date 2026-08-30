"""
AIEmployeeService Integration Tests - Context passing
Covers:
- AIEmployeeService receives context_data and injects it into messages
- No context_data → behavior unchanged
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base
from src.identity.audit import AuditService
from src.identity.rbac import RBACService
from src.workforce.employee import AIEmployeeService
from src.workforce.models import AIEmployee, AIEmployeeStatus, Department, Position
from src.workforce.registry import AIEmployeeRegistry


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_test_employee(registry: AIEmployeeRegistry) -> AIEmployee:
    """Create a test AI employee with a mock agent type."""
    from src.ai.agents import AgentType
    employee = AIEmployee(
        id=uuid4(),
        name="Test Employee",
        department=Department.RESEARCH,
        position=Position.MARKET_RESEARCHER,
        description="Test employee for context tests",
        agent_type=AgentType.GPT,
        status=AIEmployeeStatus.ACTIVE,
    )
    return await registry.register(employee)


def test_workforce_execute_task_with_context_data():
    """Test: AIEmployeeService.execute_task receives context_data and injects it into messages."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            employee = await create_test_employee(registry)

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            # Patch AgentRuntime.execute to capture messages
            from src.ai.agents import AgentRuntime
            captured_messages = []

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                captured_messages.extend(messages)
                from src.ai.agents import AgentExecution, AgentStatus, AgentContext
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Result with context",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                # Execute with context_data
                context_data = {
                    "step_results": {
                        "step-1": {"status": "completed", "result": "Market analysis done"}
                    },
                    "variables": {"market": "Vietnam"},
                }
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Execute market research",
                    context_data=context_data,
                )

            # Verify context was injected into messages
            system_messages = [m for m in captured_messages if m.get("role") == "system"]
            context_system_msgs = [
                m for m in system_messages
                if "工作流上下文" in m.get("content", "")
            ]
            assert len(context_system_msgs) >= 1, (
                "At least one system message with workflow context should be present"
            )
            ctx_content = context_system_msgs[0]["content"]
            assert "step_results" in ctx_content
            assert "Market analysis done" in ctx_content
            assert "Vietnam" in ctx_content

            # Verify user prompt is still present
            user_messages = [m for m in captured_messages if m.get("role") == "user"]
            assert len(user_messages) >= 1
            assert user_messages[-1]["content"] == "Execute market research"

            # Verify result is successful
            assert result["status"] == "completed"
            assert result["output"] == "Result with context"

    asyncio.run(_run())


def test_workforce_execute_task_no_context_data():
    """Test: AIEmployeeService.execute_task without context_data behaves as before."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            employee = await create_test_employee(registry)

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            from src.ai.agents import AgentRuntime
            captured_messages = []

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                captured_messages.extend(messages)
                from src.ai.agents import AgentExecution, AgentStatus, AgentContext
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Normal result",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                # Execute WITHOUT context_data
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Execute normal task",
                    # no context_data
                )

            # Verify NO workflow context system message was injected
            system_messages = [m for m in captured_messages if m.get("role") == "system"]
            context_system_msgs = [
                m for m in system_messages
                if "工作流上下文" in m.get("content", "")
            ]
            assert len(context_system_msgs) == 0, (
                "No workflow context system message should be present when context_data is None"
            )

            # Verify user prompt is present
            user_messages = [m for m in captured_messages if m.get("role") == "user"]
            assert len(user_messages) >= 1
            assert user_messages[-1]["content"] == "Execute normal task"

            # Verify result is successful
            assert result["status"] == "completed"
            assert result["output"] == "Normal result"

    asyncio.run(_run())


def test_workforce_execute_task_no_provider_config():
    """Test: No provider_config → keep original AgentConfig provider/model."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            employee = await create_test_employee(registry)  # no provider_config

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            from src.ai.agents import AgentRuntime, AgentType
            from src.ai.providers import ProviderType
            captured_provider = None
            captured_model = None

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                nonlocal captured_provider, captured_model
                cfg = self._registry.get(agent_type)
                captured_provider = cfg.provider
                captured_model = cfg.model_id
                from src.ai.agents import AgentExecution, AgentStatus
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Default config result",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Test default config",
                )

            # GPT default: ProviderType.OPENAI, model_id="gpt-4"
            assert captured_provider == ProviderType.OPENAI, (
                f"Expected OPENAI, got {captured_provider}"
            )
            assert captured_model == "gpt-4", (
                f"Expected gpt-4, got {captured_model}"
            )
            assert result["status"] == "completed"

    asyncio.run(_run())


def test_workforce_execute_task_with_provider_config():
    """Test: Full provider_config → use Employee specified provider/model."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            from src.ai.agents import AgentType
            employee = AIEmployee(
                id=uuid4(),
                name="Config Employee",
                department=Department.RESEARCH,
                position=Position.MARKET_RESEARCHER,
                description="Test employee with provider_config",
                agent_type=AgentType.GPT,
                status=AIEmployeeStatus.ACTIVE,
                provider_config={"provider": "ollama", "model": "qwen2.5:7b"},
            )
            await registry.register(employee)

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            from src.ai.agents import AgentRuntime, AgentType
            from src.ai.providers import ProviderType
            captured_provider = None
            captured_model = None

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                nonlocal captured_provider, captured_model
                cfg = self._registry.get(agent_type)
                captured_provider = cfg.provider
                captured_model = cfg.model_id
                from src.ai.agents import AgentExecution, AgentStatus
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Overridden config result",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Test provider config",
                )

            # Provider should be overridden to ollama
            assert captured_provider == ProviderType.OLLAMA, (
                f"Expected OLLAMA, got {captured_provider}"
            )
            # Model should be overridden to qwen2.5:7b
            assert captured_model == "qwen2.5:7b", (
                f"Expected qwen2.5:7b, got {captured_model}"
            )
            assert result["status"] == "completed"

    asyncio.run(_run())


def test_workforce_execute_task_provider_only():
    """Test: provider_config with only provider → provider overridden, model fallback."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            from src.ai.agents import AgentType
            employee = AIEmployee(
                id=uuid4(),
                name="Provider Only",
                department=Department.RESEARCH,
                position=Position.MARKET_RESEARCHER,
                description="Test employee with provider only",
                agent_type=AgentType.GPT,
                status=AIEmployeeStatus.ACTIVE,
                provider_config={"provider": "ollama"},
            )
            await registry.register(employee)

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            from src.ai.agents import AgentRuntime, AgentType
            from src.ai.providers import ProviderType
            captured_provider = None
            captured_model = None

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                nonlocal captured_provider, captured_model
                cfg = self._registry.get(agent_type)
                captured_provider = cfg.provider
                captured_model = cfg.model_id
                from src.ai.agents import AgentExecution, AgentStatus
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Provider only result",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Test provider only",
                )

            # Provider overridden to ollama
            assert captured_provider == ProviderType.OLLAMA, (
                f"Expected OLLAMA, got {captured_provider}"
            )
            # Model should fall back to GPT default (gpt-4)
            assert captured_model == "gpt-4", (
                f"Expected gpt-4 fallback, got {captured_model}"
            )
            assert result["status"] == "completed"

    asyncio.run(_run())


def test_workforce_execute_task_model_only():
    """Test: provider_config with only model → model overridden, provider fallback."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            rbac = MagicMock(spec=RBACService)
            audit = MagicMock(spec=AuditService)
            registry = AIEmployeeRegistry(session)
            from src.ai.agents import AgentType
            employee = AIEmployee(
                id=uuid4(),
                name="Model Only",
                department=Department.RESEARCH,
                position=Position.MARKET_RESEARCHER,
                description="Test employee with model only",
                agent_type=AgentType.GPT,
                status=AIEmployeeStatus.ACTIVE,
                provider_config={"model": "custom-model-v1"},
            )
            await registry.register(employee)

            service = AIEmployeeService(
                registry=registry,
                rbac_service=rbac,
                audit_service=audit,
            )

            from src.ai.agents import AgentRuntime, AgentType
            from src.ai.providers import ProviderType
            captured_provider = None
            captured_model = None

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                nonlocal captured_provider, captured_model
                cfg = self._registry.get(agent_type)
                captured_provider = cfg.provider
                captured_model = cfg.model_id
                from src.ai.agents import AgentExecution, AgentStatus
                from uuid import uuid4
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Model only result",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute):
                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Test model only",
                )

            # Provider should fall back to GPT default (OPENAI)
            assert captured_provider == ProviderType.OPENAI, (
                f"Expected OPENAI, got {captured_provider}"
            )
            # Model overridden to custom-model-v1
            assert captured_model == "custom-model-v1", (
                f"Expected custom-model-v1, got {captured_model}"
            )
            assert result["status"] == "completed"

    asyncio.run(_run())