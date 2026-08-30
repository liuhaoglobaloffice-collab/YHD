"""
CRM 执行模式测试 — 验证每条线索的 source_type 字段正确标记。

覆盖：
- LeadAcquisitionEngine 各数据源 source_type 标记
- LeadService create_lead 存储 source_type
- stats 返回 by_source_type 统计
"""

import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.crm.engines import (
    EXECUTION_MODE_MOCK,
    EXECUTION_MODE_NOT_CONFIGURED,
    EXECUTION_MODE_REAL,
    CustomsDataProvider,
    LeadAcquisitionEngine,
    SupplierDiscoveryEngine,
)
from src.crm.models import Lead
from src.crm.service import LeadService
from src.database.base import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


# ==================== LeadAcquisitionEngine ====================


class TestLeadAcquisitionEngineSourceType:
    """验证引擎返回的每条线索都带有正确的 source_type 标记。"""

    @pytest.mark.asyncio
    async def test_social_leads_always_mock(self):
        """社媒线索永远是 MOCK。"""
        engine = LeadAcquisitionEngine()
        result = await engine.run(sources=["social"], keywords=["test"], limit=1)
        leads = result["leads"]
        assert len(leads) > 0
        for lead in leads:
            assert lead["source"] == "social"
            assert lead["source_type"] == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_customs_leads_always_mock(self):
        """海关线索（通过引擎）永远是 MOCK。"""
        engine = LeadAcquisitionEngine()
        result = await engine.run(sources=["customs"], keywords=["test"], limit=1)
        leads = result["leads"]
        assert len(leads) > 0
        for lead in leads:
            assert lead["source"] == "customs"
            assert lead["source_type"] == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_google_leads_mock_without_api_key(self):
        """没有 API Key 时谷歌搜索返回 MOCK。"""
        # 确保环境变量为空
        with patch.dict(os.environ, {"GOOGLE_SEARCH_API_KEY": "", "GOOGLE_SEARCH_CX": ""}):
            engine = LeadAcquisitionEngine()
            result = await engine.run(sources=["google"], keywords=["test"], limit=1)
            leads = result["leads"]
            assert len(leads) > 0
            for lead in leads:
                assert lead["source"] == "google"
                assert lead["source_type"] == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_google_leads_real_with_api_key(self, monkeypatch):
        """有 API Key 时谷歌搜索尝试调用真实接口，因无真实 API 回退到 MOCK。"""
        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "fake-key")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "fake-cx")

        engine = LeadAcquisitionEngine()
        # 真实 API 会失败，回退到 MOCK
        result = await engine.run(sources=["google"], keywords=["test"], limit=1)
        leads = result["leads"]
        # 因为 API 调用会失败，回退到 MOCK
        assert len(leads) > 0
        for lead in leads:
            assert lead["source_type"] == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_google_real_api_success_marks_real(self, monkeypatch):
        """P0 真实获客激活：Google Custom Search API 成功响应 → 线索解析 + source_type=REAL。

        用 httpx.MockTransport 模拟真实 API 成功响应（不依赖外网），
        验证 items → 线索字段解析（title/company/website/搜索词）与 REAL 标记。
        """
        import httpx

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "test-cx")

        captured_requests = []

        def _google_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "title": "Global LED Trading Co.",
                            "link": "https://globaled.example.com",
                        },
                        {
                            "title": "Euro Hardware Import GmbH",
                            "link": "https://eurohardware.example.com",
                        },
                    ]
                },
            )

        transport = httpx.MockTransport(_google_handler)
        real_async_client = httpx.AsyncClient

        def _client_factory(*args, **kwargs):
            return real_async_client(transport=transport)

        monkeypatch.setattr("src.crm.engines.httpx.AsyncClient", _client_factory)

        engine = LeadAcquisitionEngine()
        result = await engine.run(
            sources=["google"], keywords=["LED lighting"], limit=5
        )
        leads = result["leads"]
        assert len(leads) == 2
        assert result["stats"]["google"] == 2
        for lead in leads:
            assert lead["source"] == "google"
            assert lead["source_type"] == EXECUTION_MODE_REAL, "真实 API 成功路径必须标记 REAL"
            assert lead["source_detail"] == "LED lighting"
        # 线索字段真实解析自 API 响应
        assert leads[0]["company"] == "Global LED Trading Co."
        assert leads[0]["name"] == "Global LED Trading Co."
        assert leads[0]["website"] == "https://globaled.example.com"
        assert leads[1]["company"] == "Euro Hardware Import GmbH"
        # 请求真实发往 Google Custom Search 端点并携带凭据
        assert captured_requests, "必须发起真实 HTTP 请求"
        req = captured_requests[0]
        assert "googleapis.com/customsearch/v1" in str(req.url)
        assert "key=test-key" in str(req.url)
        assert "cx=test-cx" in str(req.url)
        assert "LED+lighting+wholesale+import+company" in str(req.url)

    @pytest.mark.asyncio
    async def test_google_real_api_error_falls_back_to_mock(self, monkeypatch):
        """Google API 返回错误（如配额超限 429）→ 回退 MOCK（诚实降级不崩溃）。"""
        import httpx

        monkeypatch.setenv("GOOGLE_SEARCH_API_KEY", "test-key")
        monkeypatch.setenv("GOOGLE_SEARCH_CX", "test-cx")

        def _error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": {"message": "quota exceeded"}})

        transport = httpx.MockTransport(_error_handler)
        real_async_client = httpx.AsyncClient

        def _client_factory(*args, **kwargs):
            return real_async_client(transport=transport)

        monkeypatch.setattr("src.crm.engines.httpx.AsyncClient", _client_factory)

        engine = LeadAcquisitionEngine()
        result = await engine.run(sources=["google"], keywords=["LED"], limit=2)
        leads = result["leads"]
        assert len(leads) > 0
        for lead in leads:
            assert lead["source_type"] == EXECUTION_MODE_MOCK, "API 失败必须回退 MOCK，不得标记 REAL"

    @pytest.mark.asyncio
    async def test_all_sources_have_source_type(self):
        """所有来源的线索都标记 source_type。"""
        engine = LeadAcquisitionEngine()
        result = await engine.run(sources=["social", "google", "customs"], limit=2)
        leads = result["leads"]
        assert len(leads) > 0
        for lead in leads:
            assert "source_type" in lead
            assert lead["source_type"] in (
                EXECUTION_MODE_REAL,
                EXECUTION_MODE_MOCK,
                EXECUTION_MODE_NOT_CONFIGURED,
            )


# ==================== CustomsDataProvider ====================


class TestCustomsDataProviderSourceType:
    """验证海关数据提供商的 source_type 标记。"""

    @pytest.mark.asyncio
    async def test_mock_returns_mock(self):
        """没有 API URL 时返回 MOCK。"""
        provider = CustomsDataProvider()
        records = await provider.search(limit=1)
        assert len(records) > 0
        for r in records:
            assert r["source_type"] == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_real_api_fallback_to_mock(self, monkeypatch):
        """有 API URL 但调用失败时回退到 MOCK。"""
        monkeypatch.setenv("CUSTOMS_API_URL", "http://invalid.example.com/api")
        provider = CustomsDataProvider()
        records = await provider.search(limit=1)
        # 会回退到 mock
        assert len(records) > 0
        for r in records:
            assert r["source_type"] == EXECUTION_MODE_MOCK


# ==================== SupplierDiscoveryEngine ====================


class TestSupplierDiscoveryEngineSourceType:
    """验证供应商发现引擎的 source_type 标记。"""

    @pytest.mark.asyncio
    async def test_discover_returns_mock(self):
        """供应商发现引擎总是返回 MOCK。"""
        engine = SupplierDiscoveryEngine()
        results = await engine.discover(limit=1)
        assert len(results) > 0
        for r in results:
            assert r["source_type"] == EXECUTION_MODE_MOCK


# ==================== LeadService ====================


class TestLeadServiceSourceType:
    """验证 LeadService 正确存储和返回 source_type。"""

    @pytest.mark.asyncio
    async def test_create_lead_saves_source_type(self, db_session: AsyncSession):
        """创建线索时 source_type 正确存储。"""
        service = LeadService(db_session)
        lead = await service.create_lead(
            {
                "name": "Test Lead",
                "source": "google",
                "source_type": EXECUTION_MODE_REAL,
                "score": 70,
            },
            owner_user_id=1,
            tenant_id="tenant-1",
        )
        assert lead.source_type == EXECUTION_MODE_REAL

    @pytest.mark.asyncio
    async def test_create_lead_default_mock(self, db_session: AsyncSession):
        """未指定 source_type 时默认为 MOCK。"""
        service = LeadService(db_session)
        lead = await service.create_lead(
            {"name": "Test Lead 2", "source": "manual", "score": 50},
            owner_user_id=1,
            tenant_id="tenant-1",
        )
        assert lead.source_type == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_stats_includes_source_type_breakdown(self, db_session: AsyncSession):
        """stats 返回 by_source_type 统计。"""
        service = LeadService(db_session)
        await service.create_lead(
            {"name": "L1", "source": "google", "source_type": EXECUTION_MODE_REAL, "score": 50},
            owner_user_id=1,
        )
        await service.create_lead(
            {"name": "L2", "source": "social", "source_type": EXECUTION_MODE_MOCK, "score": 50},
            owner_user_id=1,
        )
        await service.create_lead(
            {"name": "L3", "source": "manual", "source_type": EXECUTION_MODE_MOCK, "score": 50},
            owner_user_id=1,
        )
        stats = await service.stats({1})
        assert "by_source_type" in stats
        assert stats["by_source_type"].get(EXECUTION_MODE_REAL) == 1
        assert stats["by_source_type"].get(EXECUTION_MODE_MOCK) == 2