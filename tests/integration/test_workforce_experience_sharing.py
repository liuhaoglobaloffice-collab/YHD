"""
AIEmployeeService experience sharing integration tests - Phase 2 T8.

Covers:
- Shared agent experiences are recalled (trust-based) and injected into messages.
- Successful execution stores the result summary to the shared knowledge base.
- Recall/store failures do not break the main execution flow.
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
    from src.ai.agents import AgentType
    employee = AIEmployee(
        id=uuid4(),
        name="Experience Test Employee",
        department=Department.RESEARCH,
        position=Position.MARKET_RESEARCHER,
        description="Test employee for experience sharing",
        agent_type=AgentType.GPT,
        status=AIEmployeeStatus.ACTIVE,
    )
    return await registry.register(employee)


def _mock_experience(value: str):
    """Build a Memory-like object with a value attribute."""
    m = MagicMock()
    m.value = value
    return m


def test_experience_recall_injected_into_messages():
    """Recalled shared experiences are injected as a system message."""
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

            from src.ai.agents import AgentRuntime, AgentExecution, AgentStatus
            captured_messages = []

            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                captured_messages.extend(messages)
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="Result output",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute), \
                 patch(
                     "src.knowledge.memory.MemoryService"
                 ) as MockMemSvc, \
                 patch(
                     "src.ai.agent_router.AgentRouter"
                 ) as MockRouter:
                mock_router_inst = MockRouter.return_value
                mock_router_inst.get_agent_trust_score = AsyncMock(return_value=0.8)

                mock_mem_inst = MockMemSvc.return_value
                mock_mem_inst.recall_agent_experience = AsyncMock(
                    return_value=[_mock_experience("Past sales insight A")]
                )
                mock_mem_inst.store_agent_experience = AsyncMock(return_value=None)

                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Execute with shared experience",
                )

            system_msgs = [m for m in captured_messages if m.get("role") == "system"]
            exp_msgs = [
                m for m in system_msgs if "共享经验" in m.get("content", "")
            ]
            assert len(exp_msgs) >= 1, "Shared experience system message should be injected"
            assert "Past sales insight A" in exp_msgs[0]["content"]

            mock_router_inst.get_agent_trust_score.assert_called_once_with(str(employee.id))
            mock_mem_inst.recall_agent_experience.assert_called_once()
            recall_kwargs = mock_mem_inst.recall_agent_experience.call_args.kwargs
            assert recall_kwargs["requester_trust_score"] == 0.8

            assert result["status"] == "completed"
            mock_mem_inst.store_agent_experience.assert_called_once()
            store_kwargs = mock_mem_inst.store_agent_experience.call_args.kwargs
            assert store_kwargs["task_type"] == employee.agent_type.value
            assert store_kwargs["result_summary"] == "Result output"

    asyncio.run(_run())


def test_experience_store_skipped_on_failure():
    """Failed execution does not store experience."""
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

            from src.ai.agents import AgentRuntime, AgentExecution, AgentStatus
            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.FAILED,
                    input_messages=messages,
                    output=None,
                    error="LLM failed",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute), \
                 patch(
                     "src.knowledge.memory.MemoryService"
                 ) as MockMemSvc, \
                 patch(
                     "src.ai.agent_router.AgentRouter"
                 ) as MockRouter:
                mock_router_inst = MockRouter.return_value
                mock_router_inst.get_agent_trust_score = AsyncMock(return_value=0.8)
                mock_mem_inst = MockMemSvc.return_value
                mock_mem_inst.recall_agent_experience = AsyncMock(return_value=[])
                mock_mem_inst.store_agent_experience = AsyncMock(return_value=None)

                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Failing task",
                )

            assert result["status"] == "failed"
            mock_mem_inst.store_agent_experience.assert_not_called()

    asyncio.run(_run())


def test_recall_failure_does_not_break_execution():
    """If recall raises, execution still completes."""
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

            from src.ai.agents import AgentRuntime, AgentExecution, AgentStatus
            async def mock_agent_execute(self, agent_type, messages, context,
                                          temperature=None, max_tokens=None):
                return AgentExecution(
                    execution_id=uuid4(),
                    agent_type=agent_type,
                    context=context,
                    status=AgentStatus.COMPLETED,
                    input_messages=messages,
                    output="OK",
                )

            with patch.object(AgentRuntime, 'execute', mock_agent_execute), \
                 patch(
                     "src.knowledge.memory.MemoryService"
                 ) as MockMemSvc, \
                 patch(
                     "src.ai.agent_router.AgentRouter"
                 ) as MockRouter:
                mock_router_inst = MockRouter.return_value
                mock_router_inst.get_agent_trust_score = AsyncMock(return_value=0.8)
                mock_mem_inst = MockMemSvc.return_value
                mock_mem_inst.recall_agent_experience = AsyncMock(
                    side_effect=RuntimeError("db down")
                )
                mock_mem_inst.store_agent_experience = AsyncMock(return_value=None)

                result = await service.execute_task(
                    employee_id=employee.id,
                    prompt="Task despite recall failure",
                )

            assert result["status"] == "completed"
            assert result["output"] == "OK"

    asyncio.run(_run())
