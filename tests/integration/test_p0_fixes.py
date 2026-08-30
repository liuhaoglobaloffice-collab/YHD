"""
P0 修复集成测试 — 验证三个 P0 修复的真实链路。

覆盖：
- P0-1 LLM 目标理解：parse_with_llm 提取 KPI/预算/时间/风险，无 Provider 时诚实降级
- P0-2 真实报价动作：ai_quotation → QuoteService 持久化真实报价单 + 回写 lead.quote_amount
- P0-3 获客接线修复：acquisition 动作不再 TypeError，线索批量入库并标记 source_type
"""

import os
from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 注册所有模型到 Base.metadata（含 users / leads / quotes / goals）
from src.database.base import Base


def _import_all_models():
    import src.database.provider_metrics_model  # noqa: F401
    import src.business.supplier.models  # noqa: F401
    import src.identity.models  # noqa: F401
    import src.tasks.models  # noqa: F401
    import src.database.models  # noqa: F401
    import src.crm.models  # noqa: F401
    import src.crm.quotation  # noqa: F401


_import_all_models()


# ==================== 测试基础设施 ====================


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """内存 SQLite + 完整建表。"""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class FakeGateway:
    """可控的 Provider Gateway 替身：返回预设 LLM 输出或抛错。"""

    def __init__(self, content: str = "", error: Exception = None, providers=None):
        self._content = content
        self._error = error
        self._providers = providers if providers is not None else ["openai"]

    def list_providers(self):
        return list(self._providers)

    async def complete(self, **kwargs):
        if self._error:
            raise self._error
        return SimpleNamespace(content=self._content)


# P0-1 LLM 目标解析的标准成功输出
LLM_PARSE_JSON = """
{
  "goal": "开发美国市场获取潜在客户",
  "kpi_name": "新增潜在客户数",
  "kpi_target": 100,
  "kpi_unit": "个",
  "budget_total": 2000,
  "time_start": "2026-09-01",
  "time_end": "2026-09-30",
  "constraints": ["美国市场"],
  "risk_boundaries": ["不超预算", "不碰侵权产品"],
  "priority": "high",
  "required_agents": ["sales", "marketing"]
}
"""


# ==================== P0-1: LLM 目标理解 ====================


class TestLLMGoalParsing:
    """CEOCommandProcessor.parse_with_llm 单元测试。"""

    @pytest.mark.asyncio
    async def test_llm_parse_extracts_business_elements(self, monkeypatch):
        """LLM 成功时提取 KPI/预算/时间/风险，parse_method=llm。"""
        from src.ai.command_processor import CEOCommandProcessor

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_PARSE_JSON),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm(
            "帮我开发美国市场，30天获取100个潜在客户，预算2000美元，不碰侵权产品"
        )

        assert parsed.metadata["parse_method"] == "llm"
        assert "llm_error" not in parsed.metadata
        assert parsed.goal == "开发美国市场获取潜在客户"
        assert parsed.kpi_name == "新增潜在客户数"
        assert parsed.kpi_target == 100.0
        assert parsed.kpi_unit == "个"
        assert parsed.budget_total == 2000.0
        assert parsed.time_start == "2026-09-01"
        assert parsed.time_end == "2026-09-30"
        assert set(parsed.risk_boundaries) == {"不超预算", "不碰侵权产品"}
        assert parsed.priority.value == "high"
        assert set(parsed.required_agents) == {"sales", "marketing"}

    @pytest.mark.asyncio
    async def test_llm_parse_tolerates_markdown_fence(self, monkeypatch):
        """LLM 返回 ```json 围栏时仍能解析。"""
        from src.ai.command_processor import CEOCommandProcessor

        fenced = f"```json\n{LLM_PARSE_JSON}\n```"
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=fenced),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm("开发美国市场预算2000美元")

        assert parsed.metadata["parse_method"] == "llm"
        assert parsed.kpi_target == 100.0
        assert parsed.budget_total == 2000.0

    @pytest.mark.asyncio
    async def test_llm_parse_fallback_no_provider(self, monkeypatch):
        """无可用 Provider 时诚实降级：rule_based + llm_error。"""
        from src.ai.command_processor import CEOCommandProcessor

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm("帮我开发美国市场预算2000美元")

        assert parsed.metadata["parse_method"] == "rule_based"
        assert parsed.metadata["llm_error"] == "no_provider_configured"
        # LLM 字段保持 None（老板需手填）
        assert parsed.kpi_name is None
        assert parsed.kpi_target is None
        assert parsed.budget_total is None
        assert parsed.risk_boundaries == []

    @pytest.mark.asyncio
    async def test_llm_parse_fallback_unparseable_response(self, monkeypatch):
        """LLM 输出不可解析时降级为规则解析。"""
        from src.ai.command_processor import CEOCommandProcessor

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content="抱歉，我无法处理这个请求。"),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm("开发美国市场")

        assert parsed.metadata["parse_method"] == "rule_based"
        assert parsed.metadata["llm_error"] == "unparseable_response"

    @pytest.mark.asyncio
    async def test_llm_parse_fallback_on_exception(self, monkeypatch):
        """LLM 调用抛错时降级且不中断目标创建。"""
        from src.ai.command_processor import CEOCommandProcessor

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(error=RuntimeError("provider timeout")),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm("开发美国市场")

        assert parsed.metadata["parse_method"] == "rule_based"
        assert "provider timeout" in parsed.metadata["llm_error"]
        # 规则解析的基线字段仍然可用
        assert parsed.goal

    @pytest.mark.asyncio
    async def test_llm_parse_rejects_invalid_values(self, monkeypatch):
        """非法值（负预算/坏日期/非法优先级）被拒绝，不落入 ParsedCommand。"""
        from src.ai.command_processor import CEOCommandProcessor

        bad_json = """
        {
          "goal": "测试目标",
          "kpi_target": -50,
          "budget_total": -100,
          "time_start": "not-a-date",
          "time_end": "31/12/2026",
          "priority": "ultra",
          "required_agents": ["hacker_agent", "sales"]
        }
        """
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=bad_json),
        )
        processor = CEOCommandProcessor()
        parsed = await processor.parse_with_llm("开发美国市场")

        assert parsed.metadata["parse_method"] == "llm"
        assert parsed.goal == "测试目标"
        # 非法值全部被拒绝
        assert parsed.kpi_target is None
        assert parsed.budget_total is None
        assert parsed.time_start is None
        assert parsed.time_end is None
        # 非法优先级保留规则解析结果，非法 agent 被过滤
        assert parsed.priority.value in ("low", "normal", "high", "critical")
        assert parsed.required_agents == ["sales"]

    def test_extract_json_object_variants(self):
        """_extract_json_object 对裸 JSON/围栏/垃圾输入的行为。"""
        from src.ai.command_processor import CEOCommandProcessor

        processor = CEOCommandProcessor()
        assert processor._extract_json_object('{"a": 1}') == {"a": 1}
        assert processor._extract_json_object('前置文字 {"a": 2} 后置文字') == {"a": 2}
        assert processor._extract_json_object('```json\n{"a": 3}\n```') == {"a": 3}
        assert processor._extract_json_object("") is None
        assert processor._extract_json_object("没有大括号") is None
        assert processor._extract_json_object("{broken json") is None


class TestCreateGoalFromText:
    """GoalService.create_goal_from_text 持久化测试。"""

    @pytest.mark.asyncio
    async def test_creates_goal_with_extracted_fields(self, db_session, monkeypatch):
        """一句自然语言 → 持久化目标（KPI/预算/时间来自 LLM）。"""
        from src.ai.goal_service import GoalService

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_PARSE_JSON),
        )
        service = GoalService(db_session)
        goal, parse_info = await service.create_goal_from_text(
            "帮我开发美国市场，30天获取100个潜在客户，预算2000美元",
            created_by=1,
        )

        assert goal.id is not None
        assert goal.status == "draft"
        assert goal.kpi_name == "新增潜在客户数"
        assert goal.kpi_target == 100.0
        assert goal.budget_total == 2000.0
        assert goal.time_start is not None
        assert goal.time_end is not None
        assert goal.plan_data["parse_method"] == "llm"
        assert "不碰侵权产品" in goal.plan_data["risk_boundaries"]
        assert parse_info["parse_method"] == "llm"
        assert parse_info["extracted"]["budget_total"] == 2000.0

        # 数据库真实落盘
        from src.database.models import GoalModel

        stored = await db_session.get(GoalModel, goal.id)
        assert stored is not None
        assert stored.kpi_name == "新增潜在客户数"

    @pytest.mark.asyncio
    async def test_honest_fallback_without_provider(self, db_session, monkeypatch):
        """无 Provider 时目标仍创建，但 parse_method=rule_based 且字段留空。"""
        from src.ai.goal_service import GoalService

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        service = GoalService(db_session)
        goal, parse_info = await service.create_goal_from_text(
            "开发东南亚市场", created_by=1
        )

        assert goal.id is not None
        assert goal.kpi_name is None
        assert goal.budget_total is None
        assert goal.plan_data["parse_method"] == "rule_based"
        assert goal.plan_data["llm_error"] == "no_provider_configured"
        assert parse_info["parse_method"] == "rule_based"

    @pytest.mark.asyncio
    async def test_empty_text_raises(self, db_session):
        """空文本抛 ValueError。"""
        from src.ai.goal_service import GoalService

        service = GoalService(db_session)
        with pytest.raises(ValueError, match="目标文本不能为空"):
            await service.create_goal_from_text("   ", created_by=1)


# ==================== P0-2: 真实报价动作 ====================


class TestAIQuotationAction:
    """TradeActionHandler._handle_ai_quotation → QuoteService 持久化。"""

    @pytest_asyncio.fixture
    async def lead(self, db_session):
        from src.crm.service import LeadService

        return await LeadService(db_session).create_lead(
            {
                "name": "John Miller",
                "company": "Miller Imports LLC",
                "country": "美国",
                "email": "john@millerimports.com",
                "product_interest": "LED 灯具",
                "source": "manual",
            },
            owner_user_id=1,
        )

    @pytest.mark.asyncio
    async def test_rule_based_quote_persisted_and_lead_updated(
        self, db_session, monkeypatch, lead
    ):
        """无 LLM Provider：规则生成单明细 → 报价单落盘 → lead.quote_amount 回写。"""
        from src.crm.quotation import Quote
        from src.workflow.trade_actions import TradeActionHandler

        # 强制无 Provider → 规则路径（单明细，价格=预算）
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_ai_quotation(
            {"lead_id": lead.id, "product": "LED Panel Light", "budget": 1500}
        )

        assert result["status"] == "completed", result
        assert result["generation_method"] == "rule_based"
        assert result["items_count"] == 1
        assert result["total_amount"] == 1500.0
        assert result["quote_number"]

        # 报价单真实落盘
        quote = await db_session.get(Quote, result["quote_id"])
        assert quote is not None
        assert quote.lead_id == lead.id
        assert quote.total_amount == 1500.0
        assert quote.owner_user_id == 1

        # lead.quote_amount 被回写
        await db_session.refresh(lead)
        assert lead.quote_amount == 1500.0

    @pytest.mark.asyncio
    async def test_llm_generated_multi_item_quote(self, db_session, monkeypatch, lead):
        """有 LLM Provider：多明细报价，generation_method=llm。"""
        from src.crm.quotation import Quote, QuoteItem
        from src.workflow.trade_actions import TradeActionHandler

        llm_items = (
            '[{"product_name": "LED Panel 60cm", "quantity": 100, "unit": "件", "unit_price": 2.5},'
            ' {"product_name": "LED Driver", "quantity": 100, "unit": "件", "unit_price": 1.0}]'
        )
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=llm_items),
        )
        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_ai_quotation(
            {"lead_id": lead.id, "product": "LED Panel", "budget": 500}
        )

        assert result["status"] == "completed", result
        assert result["generation_method"] == "llm"
        assert result["items_count"] == 2
        # 100 * 2.5 + 100 * 1.0 = 350
        assert result["total_amount"] == 350.0

        # 明细落盘
        stmt = select(QuoteItem).where(QuoteItem.quote_id == result["quote_id"])
        items = list((await db_session.execute(stmt)).scalars().all())
        assert len(items) == 2

        # lead.quote_amount 回写为总额
        await db_session.refresh(lead)
        assert lead.quote_amount == 350.0

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_rules(self, db_session, monkeypatch, lead):
        """LLM 输出不可解析时降级为规则单明细，仍创建真实报价单。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content="我建议您咨询销售团队"),
        )
        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_ai_quotation(
            {"lead_id": lead.id, "product": "LED Panel", "budget": 800}
        )

        assert result["status"] == "completed", result
        assert result["generation_method"] == "rule_based"
        assert result["total_amount"] == 800.0

    @pytest.mark.asyncio
    async def test_lead_not_accessible_fails(self, db_session, monkeypatch):
        """线索不存在 → status=failed（不静默成功）。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_ai_quotation(
            {"lead_id": 99999, "product": "LED Panel", "budget": 100}
        )

        assert result["status"] == "failed"
        assert "99999" in result["error"]

    @pytest.mark.asyncio
    async def test_lead_owner_isolation(self, db_session, monkeypatch, lead):
        """租户隔离：owner=2 的 handler 不能给 owner=1 的线索报价。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        handler = TradeActionHandler(db_session, owner_user_id=2)
        result = await handler._handle_ai_quotation(
            {"lead_id": lead.id, "product": "LED Panel", "budget": 100}
        )

        assert result["status"] == "failed"
        assert "无权访问" in result["error"]

    def test_parse_quote_items_variants(self):
        """_parse_quote_items 对围栏/垃圾/非法明细的处理。"""
        from src.workflow.trade_actions import TradeActionHandler

        handler = TradeActionHandler.__new__(TradeActionHandler)
        assert handler._parse_quote_items("") == []
        assert handler._parse_quote_items("no brackets here") == []
        assert handler._parse_quote_items("not json [") == []
        # 非法数量/单价被修正为合法边界
        items = handler._parse_quote_items(
            '[{"product_name": "A", "quantity": -5, "unit_price": -1},'
            ' {"product_name": "", "quantity": 2, "unit_price": 3},'
            ' "not_a_dict"]'
        )
        assert len(items) == 1
        assert items[0]["product_name"] == "A"
        assert items[0]["quantity"] == 1
        assert items[0]["unit_price"] == 0.0


# ==================== P0-3: 获客动作接线修复 ====================


class TestAcquisitionAction:
    """TradeActionHandler._handle_acquisition：签名修复 + 线索入库。"""

    @pytest.mark.asyncio
    async def test_acquisition_runs_and_saves_leads(self, db_session, monkeypatch):
        """获客动作执行成功（原实现必 TypeError）→ 线索入库 + MOCK 诚实标记。"""
        from src.crm.models import Lead
        from src.workflow.trade_actions import TradeActionHandler

        # 清空凭据 → 谷歌源走 MOCK，不发起真实 HTTP 请求
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_acquisition(
            {"keywords": "LED lighting", "lead_count": 5}
        )

        assert result["status"] == "completed", result
        assert result["leads_found"] > 0
        assert result["new_leads"] > 0
        assert result["new_leads"] == result["leads_found"]
        assert result["real_leads"] == 0
        assert result["data_source"] == "MOCK"

        # 线索真实落盘，source_type 标记 MOCK
        stmt = select(Lead).where(Lead.owner_user_id == 1)
        leads = list((await db_session.execute(stmt)).scalars().all())
        assert len(leads) == result["new_leads"]
        assert all(l.source_type == "MOCK" for l in leads)
        assert all(l.source in ("social", "google", "customs") for l in leads)

    @pytest.mark.asyncio
    async def test_acquisition_deduplicates_on_rerun(self, db_session, monkeypatch):
        """重复执行按 email/company 去重：第二次 created=0。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        handler = TradeActionHandler(db_session, owner_user_id=1)
        config = {"keywords": "LED lighting", "lead_count": 3}

        first = await handler._handle_acquisition(config)
        assert first["status"] == "completed"
        assert first["new_leads"] > 0

        second = await handler._handle_acquisition(config)
        assert second["status"] == "completed"
        assert second["new_leads"] == 0
        assert second["skipped"] == second["leads_found"]

    @pytest.mark.asyncio
    async def test_acquisition_accepts_list_keywords(self, db_session, monkeypatch):
        """keywords 支持列表形式（工作流配置可能是 list）。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_acquisition(
            {"keywords": ["solar panel", "hardware"], "lead_count": 2}
        )

        assert result["status"] == "completed"
        assert result["leads_found"] > 0

    @pytest.mark.asyncio
    async def test_acquisition_respects_lead_count(self, db_session, monkeypatch):
        """lead_count 限制每源返回数量。"""
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        handler = TradeActionHandler(db_session, owner_user_id=1)
        result = await handler._handle_acquisition(
            {"keywords": "LED", "lead_count": 1}
        )
        # 3 个源 × 每源 1 条 = 3 条
        assert result["leads_found"] == 3
        assert result["new_leads"] == 3

    @pytest.mark.asyncio
    async def test_acquisition_tenant_isolation(self, db_session, monkeypatch):
        """owner 隔离：owner=2 的动作只写自己的线索。"""
        from src.crm.models import Lead
        from src.workflow.trade_actions import TradeActionHandler

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "")

        handler = TradeActionHandler(db_session, owner_user_id=2)
        result = await handler._handle_acquisition({"keywords": "LED", "lead_count": 1})
        assert result["new_leads"] > 0

        stmt = select(Lead).where(Lead.owner_user_id == 2)
        leads = list((await db_session.execute(stmt)).scalars().all())
        assert len(leads) == result["new_leads"]
        # owner=1 无线索
        stmt1 = select(Lead).where(Lead.owner_user_id == 1)
        leads1 = list((await db_session.execute(stmt1)).scalars().all())
        assert leads1 == []


# ==================== API 层：/goals/from-text ====================


@pytest.fixture
def api_env(tmp_path):
    """隔离的 SQLite 文件库 + 应用实例。"""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "p0_fixes_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


class TestGoalFromTextAPI:
    """POST /api/v1/goals/from-text 端到端。"""

    def _login_headers(self, client):
        import uuid

        suffix = uuid.uuid4().hex[:8]
        client.post(
            "/api/v1/auth/register",
            json={
                "username": f"p0_user_{suffix}",
                "email": f"p0_{suffix}@example.com",
                "full_name": "P0 User",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"username": f"p0_user_{suffix}", "password": "testpass123"},
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    def test_from_text_creates_goal_with_parse_info(self, api_env, monkeypatch):
        """端到端：自然语言 → LLM 提取 → 目标创建 → parse_info 返回。"""
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_PARSE_JSON),
        )
        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            resp = client.post(
                "/api/v1/goals/from-text",
                json={"text": "开发美国市场，30天获取100个潜在客户，预算2000美元"},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["id"] is not None
            assert data["status"] == "draft"
            assert data["kpi_name"] == "新增潜在客户数"
            assert data["kpi_target"] == 100.0
            assert data["budget_total"] == 2000.0
            assert data["parse_info"]["parse_method"] == "llm"
            assert data["parse_info"]["extracted"]["kpi_target"] == 100.0

    def test_from_text_honest_fallback_without_llm(self, api_env, monkeypatch):
        """无 Provider 时仍创建目标，但诚实标记 rule_based。"""
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(providers=[]),
        )
        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            resp = client.post(
                "/api/v1/goals/from-text",
                json={"text": "开发东南亚市场"},
                headers=headers,
            )
            assert resp.status_code == 201, resp.text
            data = resp.json()
            assert data["kpi_name"] is None
            assert data["budget_total"] is None
            assert data["parse_info"]["parse_method"] == "rule_based"
            assert data["parse_info"]["llm_error"] == "no_provider_configured"

    def test_from_text_empty_text_rejected(self, api_env):
        """空文本返回 400。"""
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            resp = client.post(
                "/api/v1/goals/from-text",
                json={"text": "   "},
                headers=headers,
            )
            assert resp.status_code == 400
