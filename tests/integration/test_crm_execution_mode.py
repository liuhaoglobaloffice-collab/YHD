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