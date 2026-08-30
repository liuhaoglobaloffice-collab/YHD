"""
P1-G5.2: SEO 内容生成 source_type 合规 + 真实 LLM 成本记录。

覆盖：
- LLM 可用且成功 → source_type=LLM + CostTracker 落盘（provider/model/tokens/latency/status）
- LLM 调用失败 → 诚实降级规则模板，source_type=RULE_BASED + llm_error，不伪造 LLM 结果
- LLM 未配置（LLM_PROVIDER=mock）→ source_type=NOT_CONFIGURED，不写成本记录
- API 层：POST /site/seo/content/generate 返回 source_type、保存后可回读、成本落库
"""

import os
import sqlite3
import uuid
from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base


def _import_all_models():
    import src.database.models  # noqa: F401
    import src.identity.models  # noqa: F401


_import_all_models()


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


LLM_SEO_JSON = """
{
  "title": "Custom LED Light Manufacturer Guide 2026",
  "slug": "custom-led-light-manufacturer-guide",
  "meta_description": "How to choose a reliable custom LED light manufacturer in 2026.",
  "outline": ["Market overview", "Certifications", "Price comparison"],
  "tags": ["led", "manufacturer"],
  "content": "# Custom LED Guide\\n\\nFull article body about LED manufacturers.",
  "search_intent": "commercial"
}
"""


class FakeGateway:
    """可控 Provider Gateway 替身：返回带 usage 的完整响应或抛错。"""

    def __init__(self, content: str = "", error: Exception | None = None):
        self._content = content
        self._error = error

    def list_providers(self):
        return ["openai"]

    async def complete(self, **kwargs):
        if self._error:
            raise self._error
        return SimpleNamespace(
            content=self._content,
            usage=SimpleNamespace(input_tokens=120, output_tokens=340),
            provider=SimpleNamespace(value="openai"),
            model_id="gpt-4o-mini",
            response_time_ms=812.5,
        )


# ==================== 单元层：SEOEngine.generate_content ====================


class TestSEOSourceTypeCompliance:
    """SEOEngine.generate_content source_type 合规 + cost 记录。"""

    @pytest.mark.asyncio
    async def test_llm_success_source_type_and_cost_record(self, db_session, monkeypatch):
        """LLM 成功 → source_type=LLM，CostTracker 记录 provider/model/tokens/latency/status。"""
        from src.database.models import AiCostRecordModel
        from src.site_os.seo import SEOEngine

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_SEO_JSON),
        )

        engine = SEOEngine()
        data = await engine.generate_content(
            "custom led light manufacturer",
            site_name="Test Store",
            content_type="blog",
            session=db_session,
            user_id=42,
        )

        assert data["source_type"] == "LLM"
        assert data["title"] == "Custom LED Light Manufacturer Guide 2026"
        assert data["llm_error"] is None

        recs = list(
            (await db_session.execute(select(AiCostRecordModel))).scalars().all()
        )
        assert len(recs) == 1
        r = recs[0]
        assert r.user_id == 42
        assert r.provider == "openai"
        assert r.model == "gpt-4o-mini"
        assert r.input_tokens == 120
        assert r.output_tokens == 340
        assert r.status == "success"
        assert r.latency_ms == pytest.approx(812.5)
        assert (r.cost_usd or 0) > 0

    @pytest.mark.asyncio
    async def test_llm_success_without_cost_ctx_still_works(self, monkeypatch):
        """无 session/user_id 时不写成本记录，但内容与 source_type 正常。"""
        from src.site_os.seo import SEOEngine

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_SEO_JSON),
        )

        data = await SEOEngine().generate_content("solar panel supplier")
        assert data["source_type"] == "LLM"
        assert data["title"]

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_rule_based(self, db_session, monkeypatch):
        """LLM 调用失败 → 规则模板 + RULE_BASED + llm_error，不落盘成本。"""
        from src.database.models import AiCostRecordModel
        from src.site_os.seo import SEOEngine

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(error=RuntimeError("provider timeout")),
        )

        data = await SEOEngine().generate_content(
            "custom led light", session=db_session, user_id=42
        )

        assert data["source_type"] == "RULE_BASED"
        assert "provider timeout" in (data.get("llm_error") or "")
        assert data["title"]  # 模板内容仍可用

        recs = list(
            (await db_session.execute(select(AiCostRecordModel))).scalars().all()
        )
        assert recs == []  # 失败调用无响应无用量，不伪造成本记录

    @pytest.mark.asyncio
    async def test_not_configured_marks_not_configured(self, db_session, monkeypatch):
        """LLM_PROVIDER=mock → source_type=NOT_CONFIGURED（不伪装 AI 生成）。"""
        from src.database.models import AiCostRecordModel
        from src.site_os.seo import SEOEngine

        monkeypatch.setenv("LLM_PROVIDER", "mock")

        data = await SEOEngine().generate_content(
            "solar panel supplier", session=db_session, user_id=42
        )

        assert data["source_type"] == "NOT_CONFIGURED"
        assert data["title"]

        recs = list(
            (await db_session.execute(select(AiCostRecordModel))).scalars().all()
        )
        assert recs == []


# ==================== API 层：POST /site/seo/content/generate ====================


@pytest.fixture
def api_env(tmp_path):
    """隔离的 SQLite 文件库。"""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "seo_source_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield db_file
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


class TestSEOContentAPI:
    """端到端：source_type 返回 + 保存回读 + 成本落库。"""

    def _login_headers(self, client):
        suffix = uuid.uuid4().hex[:8]
        client.post(
            "/api/v1/auth/register",
            json={
                "username": f"seo_user_{suffix}",
                "email": f"seo_{suffix}@example.com",
                "full_name": "SEO User",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login = client.post(
            "/api/v1/auth/login",
            json={"username": f"seo_user_{suffix}", "password": "testpass123"},
        )
        assert login.status_code == 200, login.text
        return {"Authorization": f"Bearer {login.json()['access_token']}"}

    @staticmethod
    def _fetch_cost_rows(db_file) -> list:
        conn = sqlite3.connect(str(db_file))
        try:
            conn.row_factory = sqlite3.Row
            return list(
                conn.execute(
                    "SELECT user_id, provider, model, input_tokens, output_tokens,"
                    " cost_usd, latency_ms, status FROM ai_cost_records"
                )
            )
        finally:
            conn.close()

    def test_generate_content_llm_source_type_and_cost(self, api_env, monkeypatch):
        """真实 LLM → API 返回 source_type=LLM，成本记录落库，保存内容可回读。"""
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setattr(
            "src.ai.gateway.get_gateway",
            lambda: FakeGateway(content=LLM_SEO_JSON),
        )
        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            site = client.post(
                "/api/v1/site/sites",
                json={"domain": "test-store.example.com", "name": "Test Store"},
                headers=headers,
            )
            assert site.status_code == 201, site.text

            resp = client.post(
                "/api/v1/site/seo/content/generate",
                json={
                    "keyword": "custom led light manufacturer",
                    "content_type": "blog",
                    "save": True,
                },
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["source_type"] == "LLM"
            assert data["title"] == "Custom LED Light Manufacturer Guide 2026"
            assert data["saved_id"] is not None

            # 保存后回读：source_type 持久化
            saved = client.get("/api/v1/site/seo/contents", headers=headers)
            assert saved.status_code == 200, saved.text
            items = saved.json()
            assert len(items) >= 1
            assert items[0]["source_type"] == "LLM"

        # 成本记录落库（provider/model/tokens/latency/status）
        rows = self._fetch_cost_rows(api_env)
        assert len(rows) == 1
        r = rows[0]
        assert r["provider"] == "openai"
        assert r["model"] == "gpt-4o-mini"
        assert r["input_tokens"] == 120
        assert r["output_tokens"] == 340
        assert r["status"] == "success"
        assert (r["cost_usd"] or 0) > 0

    def test_generate_content_not_configured_is_honest(self, api_env, monkeypatch):
        """LLM_PROVIDER=mock → API 返回 NOT_CONFIGURED，不落成本记录。"""
        from fastapi.testclient import TestClient

        from src.api.app import create_app

        monkeypatch.setenv("LLM_PROVIDER", "mock")
        app = create_app()
        with TestClient(app) as client:
            headers = self._login_headers(client)
            resp = client.post(
                "/api/v1/site/seo/content/generate",
                json={
                    "keyword": "solar panel supplier",
                    "content_type": "blog",
                    "save": False,
                },
                headers=headers,
            )
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["source_type"] == "NOT_CONFIGURED"
            assert data["title"]  # 规则模板内容仍可用

        assert self._fetch_cost_rows(api_env) == []