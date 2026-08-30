"""
端到端链路验证 — P0 修复后的真实执行链。

验证链路：
1. Goal 链路:  from-text 创建（LLM 提取）→ 激活（真实 Workflow 生成）→ 执行（Task 真实执行）→ 状态落盘
2. 业务链路:  获客动作（线索真实落盘）→ 报价动作（报价单真实落盘 + lead.quote_amount 回写）

LLM Provider 说明：测试用 SmartFakeGateway 替身模拟真实 LLM 响应
（set_gateway 全局注入，覆盖 AgentRuntime / parse_with_llm / 报价明细生成所有调用点），
链路本身的每个环节（Workflow/Task/Execution/Quote/Lead）全部真实持久化。
"""

import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


# ==================== 测试基础设施 ====================


@pytest.fixture
def e2e_env(tmp_path):
    """隔离的 SQLite 文件库。"""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "e2e_chain_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield str(db_file)
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


class SmartFakeGateway:
    """按 prompt 内容分发的 LLM Provider 替身。

    - 目标解析 prompt（parse_with_llm）→ 返回结构化目标 JSON
    - 报价明细 prompt（_generate_quote_items）→ 返回报价明细 JSON 数组
    - 其余（AI 员工任务执行）→ 返回通用任务输出
    """

    GOAL_JSON = (
        '{"goal": "开发美国市场获取潜在客户", "kpi_name": "新增潜在客户数",'
        ' "kpi_target": 100, "kpi_unit": "个", "budget_total": 2000,'
        ' "time_start": "2026-09-01", "time_end": "2026-09-30",'
        ' "constraints": ["美国市场"], "risk_boundaries": ["不超预算"],'
        ' "priority": "high", "required_agents": ["sales"]}'
    )

    QUOTE_ITEMS = (
        '[{"product_name": "LED Panel 60cm", "quantity": 100, "unit": "件", "unit_price": 2.5},'
        ' {"product_name": "LED Driver", "quantity": 100, "unit": "件", "unit_price": 1.0}]'
    )

    def list_providers(self):
        return ["openai"]

    # 兼容真实启动流程：dotenv 修复后 app 启动会注册 Provider/Model，
    # 替身需接受这些注册调用（no-op），否则启动阶段 AttributeError。
    def register_provider(self, provider):
        return None

    def register_model(self, model):
        return None

    def list_models(self, provider=None, enabled_only=True):
        return []

    async def complete(self, messages=None, **kwargs):
        content = ""
        last = messages[-1]["content"] if messages else ""
        if "经营目标解析助手" in last:
            content = self.GOAL_JSON
        elif "为外贸报价单生成产品明细" in last:
            content = self.QUOTE_ITEMS
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
    """全局注入 LLM 替身（set_gateway 覆盖所有调用点）。"""
    from src.ai.gateway import reset_gateway, set_gateway

    set_gateway(SmartFakeGateway())
    yield
    reset_gateway()


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
    """创建全部门 AI 员工（Goal 激活路由必需；agent_type=gpt 走默认 Agent 配置）。

    market_analysis 模板任务覆盖 research / sales / business / ceo_assistant 四类路由。
    """
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
        # 新员工默认 CREATED 状态，需激活后才能被任务路由选中
        emp_id = resp.json()["id"]
        act = client.post(f"/api/v1/workforce/employees/{emp_id}/activate", headers=headers)
        assert act.status_code == 200, act.text
        assert act.json()["status"] == "active"
    return employees


def _import_models():
    import importlib

    importlib.import_module("src.database.provider_metrics_model")
    importlib.import_module("src.business.supplier.models")
    importlib.import_module("src.identity.models")
    importlib.import_module("src.tasks.models")
    importlib.import_module("src.database.models")


# ==================== E2E-1: Goal 全链路 ====================


class TestE2EGoalChain:
    """from-text 创建 → 激活（真实 Workflow）→ 执行（Task 真实执行）→ 状态落盘。"""

    def test_goal_from_text_to_completed(self, e2e_env, fake_llm):
        """完整目标链路：一句自然语言 → 目标 → Workflow → Task 执行 → completed。"""
        _import_models()
        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"e2e_goal_{uuid.uuid4().hex[:8]}")
            _create_default_employees(client, headers)

            # ── Step 1: LLM 目标理解创建目标 ──
            resp = client.post(
                "/api/v1/goals/from-text",
                json={"text": "帮我开发美国市场，30天获取100个潜在客户，预算2000美元"},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            goal = resp.json()
            goal_id = goal["id"]
            assert goal["status"] == "draft"
            assert goal["parse_info"]["parse_method"] == "llm"
            assert goal["kpi_name"] == "新增潜在客户数"
            assert goal["kpi_target"] == 100.0
            assert goal["budget_total"] == 2000.0

            # ── Step 2: 激活 → 真实 Workflow 生成 ──
            resp = client.post(f"/api/v1/goals/{goal_id}/activate", headers=headers)
            assert resp.status_code == 200, resp.text
            activated = resp.json()
            assert activated["status"] == "active"
            assert activated["workflow_id"], "激活必须关联真实 Workflow"
            workflow_id = activated["workflow_id"]
            # 计划数据真实生成（任务 + AI 员工分配）
            plan = activated.get("plan_data") or {}
            assert len(plan.get("tasks", [])) >= 1
            assignments = plan.get("agent_assignments", [])
            assert assignments and assignments[0]["employee_id"]

            # ── Step 3: 执行 Workflow → Task 真实执行 ──
            resp = client.post(f"/api/v1/goals/{goal_id}/execute", headers=headers)
            assert resp.status_code == 200, resp.text
            executed = resp.json()
            assert executed["status"] == "completed", executed
            assert executed["progress_pct"] == 100.0
            exec_result = (executed.get("plan_data") or {}).get("execution_result", {})
            assert exec_result.get("status") == "completed"

            # ── Step 4: 数据库真实落盘验证 ──
            db_url = os.environ["DATABASE_URL"]
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
            try:
                with engine.connect() as conn:
                    # Workflow 定义落盘
                    wf_count = conn.execute(
                        text("SELECT COUNT(*) FROM workflows WHERE id = :wid"),
                        {"wid": workflow_id},
                    ).scalar()
                    assert wf_count == 1, "Workflow 必须真实落盘"

                    # Workflow 执行记录落盘且成功
                    exec_row = conn.execute(
                        text(
                            "SELECT status, result FROM workflow_executions "
                            "WHERE workflow_id = :wid ORDER BY started_at DESC LIMIT 1"
                        ),
                        {"wid": workflow_id},
                    ).fetchone()
                    assert exec_row is not None, "执行记录必须真实落盘"
                    # WorkflowExecutionStatus 枚举值为大写（"COMPLETED"）
                    assert exec_row[0] == "COMPLETED", f"实际状态: {exec_row[0]}"

                    # Task 落盘且全部成功（真实执行，非 placeholder）
                    # 工作流任务由 TaskService 持久化到 tasks 表（TaskModel）
                    task_rows = conn.execute(
                        text("SELECT status, COUNT(*) FROM tasks GROUP BY status")
                    ).fetchall()
                    status_map = {r[0]: r[1] for r in task_rows}
                    assert status_map.get("completed", 0) >= 1, "任务必须真实执行成功"
                    assert status_map.get("failed", 0) == 0, f"存在失败任务: {status_map}"

                    # AI 成本记录（LLM 调用记账）
                    cost_count = conn.execute(
                        text("SELECT COUNT(*) FROM ai_cost_records")
                    ).scalar()
                    assert cost_count >= 1, "真实 LLM 调用必须记录成本"
            finally:
                engine.dispose()

    def test_goal_activation_requires_employee(self, e2e_env, fake_llm):
        """无可用 AI 员工时激活必须真实报错（不允许 placeholder 假成功）。"""
        _import_models()
        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"e2e_noemp_{uuid.uuid4().hex[:8]}")
            # 不创建 AI 员工

            resp = client.post(
                "/api/v1/goals/from-text",
                json={"text": "帮我开发美国市场获取客户"},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            goal_id = resp.json()["id"]

            resp = client.post(f"/api/v1/goals/{goal_id}/activate", headers=headers)
            assert resp.status_code == 400, "无员工时激活必须失败而不是假成功"
            assert "employee" in resp.json()["detail"].lower()


# ==================== E2E-2: 业务动作链路 ====================


class TestE2ETradeActions:
    """获客动作 → 线索落盘；报价动作 → 报价单落盘 + 线索回写。"""

    def test_customer_development_leads_persisted(self, e2e_env, monkeypatch):
        """客户开发模板：获客步骤 → 线索真实落盘 CRM（source_type 标记）。"""
        _import_models()
        from src.api.app import create_app

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"e2e_cust_{uuid.uuid4().hex[:8]}")

            resp = client.post(
                "/api/v1/workflows/trade-templates/customer_development/instantiate",
                json={"input_data": {"keywords": "LED lighting", "lead_count": 3}},
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["status"] == "completed"

            steps = {s["type"]: s["result"] for s in data["steps"]}
            acq = steps["acquisition"]
            assert acq["status"] == "completed"
            assert acq["new_leads"] > 0
            assert acq["data_source"] == "MOCK"  # 无凭据时诚实标记

            # 线索真实落盘
            engine = create_engine(
                os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
            )
            try:
                with engine.connect() as conn:
                    rows = conn.execute(
                        text("SELECT source_type, COUNT(*) FROM leads GROUP BY source_type")
                    ).fetchall()
                    source_map = {r[0]: r[1] for r in rows}
                    total = sum(source_map.values())
                    assert total == acq["new_leads"], "线索数必须与动作结果一致"
                    assert source_map.get("MOCK", 0) == total
            finally:
                engine.dispose()

    def test_deal_closure_quote_persisted(self, e2e_env, fake_llm):
        """报价成交流程模板：ai_quotation → 报价单真实落盘 + lead.quote_amount 回写。"""
        _import_models()
        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"e2e_deal_{uuid.uuid4().hex[:8]}")

            # 前置：创建一条线索
            lead_resp = client.post(
                "/api/v1/crm/leads",
                json={
                    "name": "John Miller",
                    "company": "Miller Imports LLC",
                    "country": "美国",
                    "email": "john@millerimports.com",
                    "product_interest": "LED 灯具",
                },
                headers=headers,
            )
            assert lead_resp.status_code in (200, 201), lead_resp.text
            lead_id = lead_resp.json()["id"]

            resp = client.post(
                "/api/v1/workflows/trade-templates/deal_closure/instantiate",
                json={
                    "input_data": {
                        "lead_id": lead_id,
                        "product": "LED Panel Light",
                        "budget": 1500,
                    }
                },
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["status"] == "completed"

            steps = {s["type"]: s["result"] for s in data["steps"]}
            quote_result = steps["ai_quotation"]
            assert quote_result["status"] == "completed", quote_result
            assert quote_result["generation_method"] == "llm"
            assert quote_result["items_count"] == 2
            # 100*2.5 + 100*1.0 = 350
            assert quote_result["total_amount"] == 350.0
            quote_id = quote_result["quote_id"]

            # 报价单落盘 + 线索回写验证
            engine = create_engine(
                os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
            )
            try:
                with engine.connect() as conn:
                    quote_row = conn.execute(
                        text(
                            "SELECT total_amount, lead_id FROM quotes WHERE id = :qid"
                        ),
                        {"qid": quote_id},
                    ).fetchone()
                    assert quote_row is not None, "报价单必须真实落盘"
                    assert float(quote_row[0]) == 350.0
                    assert str(quote_row[1]) == str(lead_id)

                    lead_amount = conn.execute(
                        text("SELECT quote_amount FROM leads WHERE id = :lid"),
                        {"lid": lead_id},
                    ).scalar()
                    assert lead_amount is not None, "lead.quote_amount 必须被回写"
                    assert float(lead_amount) == 350.0
            finally:
                engine.dispose()

    def test_full_business_chain_acquisition_to_quote(self, e2e_env, fake_llm, monkeypatch):
        """完整业务闭环：获客（线索落盘）→ 报价（报价单落盘 + 线索金额回写）。"""
        _import_models()
        from src.api.app import create_app

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        app = create_app()
        with TestClient(app) as client:
            headers = _register_and_login(client, f"e2e_full_{uuid.uuid4().hex[:8]}")

            # ── 环节 1: 自动获客 → 线索落盘 ──
            resp = client.post(
                "/api/v1/workflows/trade-templates/customer_development/instantiate",
                json={"input_data": {"keywords": "LED lighting", "lead_count": 2}},
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            acq_result = {
                s["type"]: s["result"] for s in resp.json()["steps"]
            }["acquisition"]
            assert acq_result["new_leads"] > 0

            # ── 环节 2: 取第一条线索，发起报价 ──
            engine = create_engine(
                os.environ["DATABASE_URL"], connect_args={"check_same_thread": False}
            )
            try:
                with engine.connect() as conn:
                    lead_row = conn.execute(
                        text("SELECT id FROM leads ORDER BY id LIMIT 1")
                    ).fetchone()
                assert lead_row is not None, "获客后线索必须已落盘"
                lead_id = lead_row[0]
            finally:
                engine.dispose()

            resp = client.post(
                "/api/v1/workflows/trade-templates/deal_closure/instantiate",
                json={
                    "input_data": {
                        "lead_id": lead_id,
                        "product": "LED Panel Light",
                        "budget": 800,
                    }
                },
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            quote_result = {
                s["type"]: s["result"] for s in resp.json()["steps"]
            }["ai_quotation"]
            assert quote_result["status"] == "completed", quote_result
            assert quote_result["total_amount"] == 350.0

            # ── 环节 3: 双向落盘验证 ──
            try:
                with engine.connect() as conn:
                    # 报价单落盘且关联获客线索
                    quote_row = conn.execute(
                        text(
                            "SELECT total_amount, lead_id FROM quotes "
                            "WHERE id = :qid"
                        ),
                        {"qid": quote_result["quote_id"]},
                    ).fetchone()
                    assert quote_row is not None
                    assert str(quote_row[1]) == str(lead_id)
                    # 线索金额回写
                    amount = conn.execute(
                        text("SELECT quote_amount FROM leads WHERE id = :lid"),
                        {"lid": lead_id},
                    ).scalar()
                    assert float(amount) == 350.0
            finally:
                engine.dispose()
