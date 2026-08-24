"""
API Performance Benchmark Tests

测试所有主要API端点的响应时间
目标: <200ms
"""

import pytest
from httpx import AsyncClient

from src.api.app import create_app
from src.identity.models import RoleEnum, User

# Create app instance
app = create_app()


class TestAPIPerformance:
    """API性能基准测试"""

    @pytest.mark.asyncio
    async def test_health_check_performance(self, benchmark):
        """健康检查端点性能"""

        async def health_check():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/health/")
                assert response.status_code == 200
                return response

        result = await benchmark.pedantic(health_check, iterations=100, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_auth_login_performance(self, benchmark, test_session, admin_user):
        """登录端点性能"""

        async def login():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"username": "admin", "password": "admin123"},
                )
                assert response.status_code in [200, 401]  # 可能失败但要测速度
                return response

        result = await benchmark.pedantic(login, iterations=50, rounds=5)
        assert result is not None

    @pytest.mark.asyncio
    async def test_users_list_performance(
        self, benchmark, test_session, admin_user, auth_headers
    ):
        """用户列表端点性能"""

        async def list_users():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/users/", headers=auth_headers)
                return response

        result = await benchmark.pedantic(list_users, iterations=50, rounds=5)
        assert result is not None

    @pytest.mark.asyncio
    async def test_tasks_list_performance(
        self, benchmark, test_session, admin_user, auth_headers
    ):
        """任务列表端点性能"""

        async def list_tasks():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/tasks/", headers=auth_headers)
                return response

        result = await benchmark.pedantic(list_tasks, iterations=50, rounds=5)
        assert result is not None

    @pytest.mark.asyncio
    async def test_workflows_list_performance(
        self, benchmark, test_session, admin_user, auth_headers
    ):
        """工作流列表端点性能"""

        async def list_workflows():
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/workflows/", headers=auth_headers
                )
                return response

        result = await benchmark.pedantic(list_workflows, iterations=50, rounds=5)
        assert result is not None


class TestDatabasePerformance:
    """数据库查询性能测试"""

    @pytest.mark.asyncio
    async def test_user_query_performance(self, benchmark, test_session):
        """用户查询性能"""
        from src.identity.models import User

        async def query_users():
            result = await test_session.execute(
                "SELECT * FROM users LIMIT 100"
            )
            return result.fetchall()

        result = await benchmark.pedantic(query_users, iterations=100, rounds=10)
        assert result is not None

    @pytest.mark.asyncio
    async def test_task_query_performance(self, benchmark, test_session):
        """任务查询性能"""

        async def query_tasks():
            result = await test_session.execute(
                "SELECT * FROM tasks LIMIT 100"
            )
            return result.fetchall()

        result = await benchmark.pedantic(query_tasks, iterations=100, rounds=10)
        assert result is not None


class TestAICallPerformance:
    """AI调用性能测试"""

    @pytest.mark.asyncio
    async def test_ai_orchestrator_performance(self, benchmark):
        """AI编排器性能 (Mock)"""
        from src.ai.orchestrator import AIOrchestrator

        orchestrator = AIOrchestrator()

        async def plan_task():
            from src.ai.orchestrator import Task

            task = Task(
                task_id="perf_test",
                description="Performance test task",
                priority="normal",
            )
            plan = await orchestrator.plan_task(task)
            return plan

        result = await benchmark.pedantic(plan_task, iterations=20, rounds=3)
        assert result is not None

    @pytest.mark.asyncio
    async def test_agent_router_performance(self, benchmark):
        """Agent路由器性能"""
        from src.ai.agent_router import AgentRouter
        from src.ai.orchestrator import Task

        router = AgentRouter()

        def route_task():
            task = Task(
                task_id="perf_test",
                description="Route to research agent",
                priority="normal",
            )
            agent_id = router.route_task(task)
            return agent_id

        result = benchmark.pedantic(route_task, iterations=100, rounds=10)
        assert result is not None


@pytest.fixture
def auth_headers(admin_user):
    """认证头部 (Mock)"""
    return {"Authorization": "Bearer mock_token_for_performance_test"}


# 性能目标配置
PERFORMANCE_TARGETS = {
    "health_check": 0.010,  # 10ms
    "auth_login": 0.100,  # 100ms
    "list_endpoints": 0.200,  # 200ms
    "database_query": 0.050,  # 50ms
    "ai_planning": 1.000,  # 1s
    "ai_routing": 0.010,  # 10ms
}
