"""Business Scheduler 集成测试 — P0 老板不在线自主经营调度。

验证：
- run_once 自动执行 active Goal（复用 GoalService 真实执行链，结果真实落盘）
- 执行完成后终态 Goal 不重复执行
- SCHEDULER_AUTO_ACTIVATE 开关行为（draft 自动激活 / 默认不动）
- 过期记忆清理（复用 AgentMemoryStore 分级策略，核心记忆保留）
- 单个 Goal 执行失败不影响调度周期（失败隔离）
- start/stop 生命周期幂等
- /health/ready 暴露调度器状态（诚实展示，不参与健康判定）

LLM Provider 说明：与 test_e2e_chain.py 一致，用 SmartFakeGateway 替身
（set_gateway 全局注入），链路每个环节（Workflow/Task/Execution/Cost）
全部真实持久化。
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# ==================== 测试基础设施 ====================


@pytest.fixture
def sched_env(tmp_path):
    """隔离的 SQLite 文件库（与 e2e_env 相同模式）。"""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "scheduler_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield str(db_file)
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


class SmartFakeGateway:
    """按 prompt 内容分发的 LLM Provider 替身（与 e2e 链路测试一致）。"""

    GOAL_JSON = (
        '{"goal": "开发美国市场获取潜在客户", "kpi_name": "新增潜在客户数",'
        ' "kpi_target": 100, "kpi_unit": "个", "budget_total": 2000,'
        ' "time_start": "2026-09-01", "time_end": "2026-09-30",'
        ' "constraints": ["美国市场"], "risk_boundaries": ["不超预算"],'
        ' "priority": "high", "required_agents": ["sales"]}'
    )

    def list_providers(self):
        return ["openai"]

    # 兼容真实启动流程：app 启动会注册 Provider/Model，替身需接受这些注册调用
    # （no-op），否则启动阶段 AttributeError。list_models 返回空，由 parse_with_llm
    # 回退到默认模型名。
    def register_provider(self, provider):
        return None

    def register_model(self, model):
        return None

    def list_models(self, provider=None, enabled_only=True):
        return []

    async def complete(self, messages=None, **kwargs):
        last = messages[-1]["content"] if messages else ""
        if "经营目标解析助手" in last:
            content = self.GOAL_JSON
        else:
            content = "任务执行完成：已基于目标完成分析并输出结论。"
        return SimpleNamespace(
            content=content,
            usage=SimpleNamespace(input_tokens=50, output_tokens=100),
            provider=SimpleNamespace(value="openai"),
            model_id="gpt-4o-mini",
            response_time_ms=120.0,
        )


@pytest.fixture
def fake_llm():
    from src.ai.gateway import reset_gateway, set_gateway

    set_gateway(SmartFakeGateway())
    yield
    reset_gateway()


@pytest_asyncio.fixture
async def sched_session_factory(sched_env):
    """连接同一 SQLite 文件的独立 async 会话工厂（调度器使用）。"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{sched_env}", echo=False
    )
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _scheduler_settings(auto_activate: bool = False):
    """调度器配置替身（仅 run_once 用到的字段）。"""
    return SimpleNamespace(
        scheduler_enabled=True,
        scheduler_interval_seconds=300,
        scheduler_auto_activate=auto_activate,
        scheduler_max_goals_per_cycle=5,
    )


def _register_and_login(client, username):
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": username,
            "password": "testpass123",
            "role": "admin",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "testpass123"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_default_employees(client, headers):
    """创建全部门 AI 员工（Goal 激活路由必需）。"""
    employees = [
        ("调研专员小研", "research", "market_researcher", "负责市场调研与竞争分析"),
        ("销售专员小美", "sales", "sales_representative", "负责客户开发与跟进"),
        ("运营专员小运", "operations", "operations_coordinator", "负责流程与数据整理"),
        ("CEO 助理小助", "ceo_office", "ceo_assistant", "负责汇总报告"),
    ]
    for name, dept, position, desc in employees:
        resp = client.post(
            "/api/v1/workforce/employees",
            json={
                "name": name,
                "department": dept,
                "position": position,
                "description": desc,
                "agent_type": "gpt",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text
        emp_id = resp.json()["id"]
        act = client.post(f"/api/v1/workforce/employees/{emp_id}/activate", headers=headers)
        assert act.status_code == 200, act.text


def _create_draft_goal(client, headers):
    """通过 from-text API 创建 draft 目标（真实 LLM 解析链路）。"""
    resp = client.post(
        "/api/v1/goals/from-text",
        json={"text": "帮我开发美国市场，30天获取100个潜在客户，预算2000美元"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    goal = resp.json()
    assert goal["status"] == "draft"
    return goal


def _import_models():
    import importlib

    importlib.import_module("src.database.provider_metrics_model")
    importlib.import_module("src.business.supplier.models")
    importlib.import_module("src.identity.models")
    importlib.import_module("src.tasks.models")
    importlib.import_module("src.database.models")


def _sync_engine(sched_env):
    return create_engine(
        f"sqlite:///{sched_env}", connect_args={"check_same_thread": False}
    )


# ==================== Goal 自主执行（老板不在线核心环）====================


class TestSchedulerGoalExecution:
    """run_once 自动执行 active Goal → 真实落盘 → 终态不重复。"""

    @pytest.mark.asyncio
    async def test_run_once_executes_active_goal(self, sched_env, fake_llm, sched_session_factory):
        """active Goal 经调度周期真实执行并落盘（Workflow/Task/Cost 全链）。"""
        _import_models()
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_exec_{uuid.uuid4().hex[:8]}")
            _create_default_employees(client, headers)
            goal = _create_draft_goal(client, headers)

            # 手动激活 → active（模拟老板设定的进行中目标）
            resp = client.post(f"/api/v1/goals/{goal['id']}/activate", headers=headers)
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "active"

            # ── 调度周期：老板不在线，调度器接管执行 ──
            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings()
            )
            result = await scheduler.run_once()

            assert result["goals_executed"] == 1
            assert result["goals_activated"] == 0  # auto_activate 默认关闭

            # ── 真实落盘验证 ──
            engine = _sync_engine(sched_env)
            try:
                with engine.connect() as conn:
                    status = conn.execute(
                        text("SELECT status FROM goals WHERE id = :gid"),
                        {"gid": goal["id"]},
                    ).scalar()
                    assert status == "completed", f"调度执行后目标应为 completed，实际 {status}"

                    task_rows = conn.execute(
                        text("SELECT status, COUNT(*) FROM tasks GROUP BY status")
                    ).fetchall()
                    status_map = {r[0]: r[1] for r in task_rows}
                    assert status_map.get("completed", 0) >= 1, "任务必须真实执行成功"

                    cost_count = conn.execute(
                        text("SELECT COUNT(*) FROM ai_cost_records")
                    ).scalar()
                    assert cost_count >= 1, "真实 LLM 调用必须记录成本"
            finally:
                engine.dispose()

            # ── 终态不重复执行 ──
            result2 = await scheduler.run_once()
            assert result2["goals_executed"] == 0, "completed 目标不应被重复执行"

    @pytest.mark.asyncio
    async def test_run_once_empty_cycle(self, sched_env, fake_llm, sched_session_factory):
        """空库调度周期正常返回（无目标时零执行，不报错）。"""
        _import_models()
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_empty_{uuid.uuid4().hex[:8]}")
            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings()
            )
            result = await scheduler.run_once()
            assert result == {
                "goals_activated": 0,
                "goals_executed": 0,
                "memories_cleaned": 0,
            }

    @pytest.mark.asyncio
    async def test_goal_execution_failure_isolated(
        self, sched_env, fake_llm, sched_session_factory, monkeypatch
    ):
        """单个 Goal 执行异常不影响调度周期（失败隔离，不崩溃）。"""
        _import_models()
        from src.ai.goal_service import GoalService
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_fail_{uuid.uuid4().hex[:8]}")
            _create_default_employees(client, headers)
            goal = _create_draft_goal(client, headers)
            resp = client.post(f"/api/v1/goals/{goal['id']}/activate", headers=headers)
            assert resp.status_code == 200, resp.text

            # 注入执行异常（模拟执行链故障；调度器必须捕获并继续）
            async def _boom(self, goal_id, user):
                raise RuntimeError("模拟执行链故障")

            monkeypatch.setattr(GoalService, "execute_goal_workflow", _boom)

            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings()
            )
            result = await scheduler.run_once()  # 不应抛出异常
            assert result["goals_executed"] == 0

            # 周期计数正常推进（调度器存活）
            assert scheduler.status()["runs"] == 1
            assert scheduler.status()["last_error"] is None  # 异常在 Goal 级被隔离


# ==================== 草稿自动激活（完全自主开关）====================


class TestSchedulerAutoActivate:
    """SCHEDULER_AUTO_ACTIVATE 开关行为。"""

    @pytest.mark.asyncio
    async def test_auto_activate_draft_when_enabled(
        self, sched_env, fake_llm, sched_session_factory
    ):
        """auto_activate 开启：draft → 同周期激活 + 执行。"""
        _import_models()
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_auto_{uuid.uuid4().hex[:8]}")
            _create_default_employees(client, headers)
            goal = _create_draft_goal(client, headers)

            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings(auto_activate=True)
            )
            result = await scheduler.run_once()

            assert result["goals_activated"] == 1
            assert result["goals_executed"] == 1, "激活后同周期应继续执行"

            engine = _sync_engine(sched_env)
            try:
                with engine.connect() as conn:
                    status = conn.execute(
                        text("SELECT status FROM goals WHERE id = :gid"),
                        {"gid": goal["id"]},
                    ).scalar()
                    assert status == "completed"
            finally:
                engine.dispose()

    @pytest.mark.asyncio
    async def test_draft_untouched_when_disabled(
        self, sched_env, fake_llm, sched_session_factory
    ):
        """auto_activate 关闭（默认）：draft 目标不被调度器碰。"""
        _import_models()
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_keep_{uuid.uuid4().hex[:8]}")
            _create_default_employees(client, headers)
            goal = _create_draft_goal(client, headers)

            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings(auto_activate=False)
            )
            result = await scheduler.run_once()

            assert result["goals_activated"] == 0
            assert result["goals_executed"] == 0

            engine = _sync_engine(sched_env)
            try:
                with engine.connect() as conn:
                    status = conn.execute(
                        text("SELECT status FROM goals WHERE id = :gid"),
                        {"gid": goal["id"]},
                    ).scalar()
                    assert status == "draft", "默认配置下 draft 目标必须保持不动"
            finally:
                engine.dispose()


# ==================== 过期记忆清理 ====================


class TestSchedulerMemoryCleanup:
    """调度周期的过期记忆清理（复用 AgentMemoryStore 分级策略）。"""

    @pytest.mark.asyncio
    async def test_expired_memory_cleaned_core_kept(
        self, sched_env, fake_llm, sched_session_factory
    ):
        """过期短期记忆被清理；核心记忆永久保留。"""
        _import_models()
        from src.api.app import create_app
        from src.scheduler.service import BusinessScheduler

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"sched_mem_{uuid.uuid4().hex[:8]}")

            # 直接落盘两条记忆：一条过期、一条核心
            async with sched_session_factory() as session:
                from src.database.models import AgentMemoryModel

                expired = AgentMemoryModel(
                    user_id=1,
                    agent_id="agent-x",
                    role="user",
                    content="过期短期记忆",
                    memory_level="short_term",
                    importance=0.3,
                    is_core=False,
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
                core = AgentMemoryModel(
                    user_id=1,
                    agent_id="agent-x",
                    role="assistant",
                    content="核心业务决策",
                    memory_level="core",
                    importance=0.9,
                    is_core=True,
                    expires_at=None,
                )
                session.add_all([expired, core])
                await session.commit()

            scheduler = BusinessScheduler(
                sched_session_factory, settings=_scheduler_settings()
            )
            result = await scheduler.run_once()

            assert result["memories_cleaned"] == 1, "应清理 1 条过期记忆"

            engine = _sync_engine(sched_env)
            try:
                with engine.connect() as conn:
                    remaining = conn.execute(
                        text("SELECT content FROM agent_memories")
                    ).fetchall()
                    assert [r[0] for r in remaining] == ["核心业务决策"]
            finally:
                engine.dispose()


# ==================== 生命周期与状态暴露 ====================


class TestSchedulerLifecycle:
    """start/stop 生命周期幂等 + health 状态展示。"""

    @pytest.mark.asyncio
    async def test_start_stop_idempotent(self, sched_env, sched_session_factory):
        """start/stop 幂等，状态字段如实反映。"""
        _import_models()
        from src.scheduler.service import BusinessScheduler

        scheduler = BusinessScheduler(
            sched_session_factory, settings=_scheduler_settings()
        )
        assert not scheduler.is_running

        scheduler.start()
        assert scheduler.is_running
        scheduler.start()  # 幂等：重复启动不创建第二个任务
        assert scheduler.is_running

        status = scheduler.status()
        assert status["running"] is True
        assert status["enabled"] is True
        assert status["auto_activate"] is False

        await scheduler.stop()
        assert not scheduler.is_running
        await scheduler.stop()  # 幂等：重复停止不报错

    @pytest.mark.asyncio
    async def test_interval_floor_enforced(self, sched_env, sched_session_factory):
        """误配置的高频间隔被钳制到最小 30 秒（防高频空转）。"""
        _import_models()
        from src.scheduler.service import BusinessScheduler

        settings = SimpleNamespace(
            scheduler_enabled=True,
            scheduler_interval_seconds=1,  # 误配置
            scheduler_auto_activate=False,
            scheduler_max_goals_per_cycle=5,
        )
        scheduler = BusinessScheduler(sched_session_factory, settings=settings)
        assert scheduler.interval_seconds == 30

    def test_health_ready_reports_scheduler_status(self, sched_env, fake_llm):
        """/health/ready 暴露调度器状态（默认关闭，不影响健康判定）。"""
        _import_models()
        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/v1/health/ready")
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert "scheduler" in data, "ready 检查必须暴露调度器状态"
            sched = data["scheduler"]
            assert sched["enabled"] is False  # 默认关闭（诚实展示）
            assert sched["running"] is False
            # 调度器为可选组件：不参与 checks 健康判定
            assert "scheduler" not in data["checks"]
