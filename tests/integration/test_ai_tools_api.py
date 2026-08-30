"""
Integration tests for AI Tools API routes.

Tests the API layer for tool execution and approval flow.
Uses the established project pattern: sync test functions with asyncio.run().
"""

import asyncio
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.base import Base


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


# ============================================================================
# API Route Registration Tests
# ============================================================================


def _make_test_app():
    """Create a test app with auth dependencies overridden."""
    from src.api.app import create_app
    from src.api.dependencies import get_current_user
    from src.api.dependencies.permissions import require_permission
    from src.identity.models import RoleEnum, User

    app = create_app()

    test_user = User(
        id=1,
        username="test_admin",
        email="test@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
        role=RoleEnum.ADMIN,
    )

    async def get_user_override():
        return test_user

    async def perm_override(*args, **kwargs):
        return None

    app.dependency_overrides[get_current_user] = get_user_override
    app.dependency_overrides[require_permission] = perm_override

    return app


def test_tools_route_registered():
    """Verify the tools route is registered in the app."""
    app = _make_test_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "total" in data


def test_execute_unknown_tool_returns_denied():
    """POST /api/v1/tools/execute with unknown tool returns 200 with DENIED status."""
    app = _make_test_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tools/execute",
            json={
                "tool_id": "unknown_tool",
                "parameters": {},
                "trace_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "denied"
        assert "error" in data


def test_execute_approved_unknown_execution_returns_404():
    """POST /api/v1/tools/execute-approved with unknown execution returns 404."""
    app = _make_test_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tools/execute-approved",
            json={
                "execution_id": "00000000-0000-0000-0000-000000000099",
                "approval_id": "999",
                "trace_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert response.status_code == 404


# ============================================================================
# ToolRegistry Unit Tests
# ============================================================================


def test_tool_registry_execute_low_risk_tool():
    """Test that a low-risk tool is executed directly via ToolRegistry."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.tools import ToolCategory, ToolConfig, ToolRegistry, ToolStatus
            from src.governance.approval import ApprovalService
            from src.governance.risk import RiskEvaluator
            from src.identity.audit import AuditService
            from src.identity.models import RiskLevel
            from src.security.policy import PolicyEngine

            registry = ToolRegistry(
                audit_service=AuditService(),
                policy_engine=PolicyEngine(),
                approval_service=ApprovalService(session),
                risk_evaluator=RiskEvaluator(),
                session=session,
            )

            async def test_handler(params):
                return {"result": "success", "input": params}

            config = ToolConfig(
                tool_id="test_low_risk_tool",
                name="Test Low Risk Tool",
                description="A test tool with low risk",
                category=ToolCategory.ANALYSIS,
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                allowed_agents={"*"},
            )
            registry.register_tool(config, test_handler)

            execution = await registry.execute(
                tool_id="test_low_risk_tool",
                parameters={"key": "value"},
                trace_id=UUID("00000000-0000-0000-0000-000000000001"),
                agent_type="test_agent",
                actor_id=UUID("00000000-0000-0000-0000-000000000002"),
            )

            assert execution.status == ToolStatus.COMPLETED
            assert execution.result == {"result": "success", "input": {"key": "value"}}
            assert execution.error is None

    asyncio.run(_run())


def test_tool_registry_execute_disabled_tool():
    """Test that executing a disabled tool returns DENIED status."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.tools import ToolCategory, ToolConfig, ToolRegistry, ToolStatus
            from src.governance.approval import ApprovalService
            from src.governance.risk import RiskEvaluator
            from src.identity.audit import AuditService
            from src.identity.models import RiskLevel
            from src.security.policy import PolicyEngine

            registry = ToolRegistry(
                audit_service=AuditService(),
                policy_engine=PolicyEngine(),
                approval_service=ApprovalService(session),
                risk_evaluator=RiskEvaluator(),
                session=session,
            )

            async def never_called(params):
                pytest.fail("Handler should not be called for disabled tool")

            config = ToolConfig(
                tool_id="test_disabled_tool",
                name="Disabled Tool",
                description="A disabled tool",
                category=ToolCategory.SYSTEM,
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                enabled=False,
                allowed_agents={"*"},
            )
            registry.register_tool(config, never_called)

            execution = await registry.execute(
                tool_id="test_disabled_tool",
                parameters={},
                trace_id=UUID("00000000-0000-0000-0000-000000000001"),
            )

            assert execution.status == ToolStatus.DENIED
            assert "disabled" in execution.error.lower()

    asyncio.run(_run())


def test_tool_registry_execute_approval_required():
    """Test that a tool requiring approval returns PENDING status."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.tools import ToolCategory, ToolConfig, ToolRegistry, ToolStatus
            from src.governance.approval import ApprovalService
            from src.governance.risk import RiskEvaluator
            from src.identity.audit import AuditService
            from src.identity.models import RiskLevel
            from src.identity.models import User
            from src.security.policy import PolicyEngine

            # Register a test user needed for approval
            user = User(
                id=1,
                username="approval_user",
                email="approval@test.com",
                hashed_password="x",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()

            registry = ToolRegistry(
                audit_service=AuditService(),
                policy_engine=PolicyEngine(),
                approval_service=ApprovalService(session),
                risk_evaluator=RiskEvaluator(),
                session=session,
            )

            async def handler(params):
                return {"result": "executed"}

            config = ToolConfig(
                tool_id="approval_required_tool",
                name="Approval Required Tool",
                description="Tool that requires approval",
                category=ToolCategory.SYSTEM,
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                allowed_agents={"*"},
            )
            registry.register_tool(config, handler)

            execution = await registry.execute(
                tool_id="approval_required_tool",
                parameters={"action": "delete"},
                trace_id=UUID("00000000-0000-0000-0000-000000000001"),
                actor_id=UUID("00000000-0000-0000-0000-000000000001"),
            )

            # Should return PENDING because the tool requires manual approval
            assert execution.status == ToolStatus.PENDING
            assert execution.approval_id is not None
            assert "requires manual approval" in execution.error.lower()

    asyncio.run(_run())


def test_tool_registry_list_tools():
    """Test listing registered tools with filtering."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.tools import ToolCategory, ToolConfig, ToolRegistry, ToolStatus
            from src.governance.approval import ApprovalService
            from src.governance.risk import RiskEvaluator
            from src.identity.audit import AuditService
            from src.identity.models import RiskLevel
            from src.security.policy import PolicyEngine

            registry = ToolRegistry(
                audit_service=AuditService(),
                policy_engine=PolicyEngine(),
                approval_service=ApprovalService(session),
                risk_evaluator=RiskEvaluator(),
                session=session,
            )

            async def handler(params):
                return {}

            # Register multiple tools
            for i in range(3):
                config = ToolConfig(
                    tool_id=f"tool_{i}",
                    name=f"Tool {i}",
                    description=f"Test tool {i}",
                    category=ToolCategory.ANALYSIS,
                    risk_level=RiskLevel.LOW,
                    requires_approval=False,
                    allowed_agents={"*"},
                )
                registry.register_tool(config, handler)

            # List all enabled tools
            tools = registry.list_tools(enabled_only=True)
            assert len(tools) == 3

            # List with category filter
            analysis_tools = registry.list_tools(category=ToolCategory.ANALYSIS, enabled_only=True)
            assert len(analysis_tools) == 3

            # List system tools (none registered)
            system_tools = registry.list_tools(category=ToolCategory.SYSTEM, enabled_only=True)
            assert len(system_tools) == 0

    asyncio.run(_run())


def test_tool_registry_idempotency():
    """Test that idempotency key prevents duplicate execution."""
    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            from src.ai.tools import ToolCategory, ToolConfig, ToolRegistry, ToolStatus
            from src.governance.approval import ApprovalService
            from src.governance.risk import RiskEvaluator
            from src.identity.audit import AuditService
            from src.identity.models import RiskLevel
            from src.security.policy import PolicyEngine

            registry = ToolRegistry(
                audit_service=AuditService(),
                policy_engine=PolicyEngine(),
                approval_service=ApprovalService(session),
                risk_evaluator=RiskEvaluator(),
                session=session,
            )

            call_count = 0

            async def handler(params):
                nonlocal call_count
                call_count += 1
                return {"call_count": call_count}

            config = ToolConfig(
                tool_id="idempotent_tool",
                name="Idempotent Tool",
                description="Tool supporting idempotent execution",
                category=ToolCategory.ANALYSIS,
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                allowed_agents={"*"},
            )
            registry.register_tool(config, handler)

            # First execution
            result1 = await registry.execute(
                tool_id="idempotent_tool",
                parameters={},
                trace_id=UUID("00000000-0000-0000-0000-000000000001"),
                idempotency_key="unique_key_1",
            )
            assert result1.status == ToolStatus.COMPLETED
            assert result1.result == {"call_count": 1}

            # Second execution with same key - should be deduplicated
            result2 = await registry.execute(
                tool_id="idempotent_tool",
                parameters={},
                trace_id=UUID("00000000-0000-0000-0000-000000000001"),
                idempotency_key="unique_key_1",
            )
            assert result2.status == ToolStatus.COMPLETED
            # Handler was still called only once
            assert call_count == 1

    asyncio.run(_run())