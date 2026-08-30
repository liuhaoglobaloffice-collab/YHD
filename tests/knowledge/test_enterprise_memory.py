"""
P1-G6.1: EnterpriseMemory facade 测试 —— 统一双记忆系统。

覆盖：
- 业务记忆写入/召回（origin=knowledge）
- 会话记忆写入/召回（origin=agent）
- recall_agent_messages 输出 LLM 消息结构
- list_all 合并双系统并标记 origin / kind 过滤跨系统生效
- 无 KNOWLEDGE_READ 权限用户：仅查会话记忆可用，查业务记忆被拒
- delete 按 origin 路由（含越权与不存在）
- mark_agent_core 标记永久保留
- overview 双系统统计
"""

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.errors import NotFoundError, PermissionDeniedError
from src.database.base import Base
from src.database.models import AgentMemoryModel
from src.identity.audit import AuditService
from src.identity.models import User
from src.identity.rbac import RBACService
from src.knowledge.enterprise_memory import (
    ORIGIN_AGENT,
    ORIGIN_KNOWLEDGE,
    EnterpriseMemory,
)
from src.knowledge.memory import MemoryType


class MockAudit(AuditService):
    """Audit stub that swallows log calls."""

    @staticmethod
    async def log(*args, **kwargs):
        pass

    @staticmethod
    async def log_permission_denied(*args, **kwargs):
        pass


async def create_test_session():
    """Create in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def create_test_user(user_id=1, is_superuser=True):
    user = User()
    user.id = user_id
    user.username = f"test_user_{user_id}"
    user.is_active = True
    user.is_superuser = is_superuser
    return user


def _facade(session) -> EnterpriseMemory:
    return EnterpriseMemory(
        session=session, rbac_service=RBACService(session), audit_service=MockAudit()
    )


# ============================================================================
# 业务记忆（knowledge）
# ============================================================================


def test_business_memory_roundtrip():
    """写入业务记忆后可按键召回，且标记 origin=knowledge。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            item = await facade.remember_business(
                user, key="发货偏好", value="默认 DHL 3日达"
            )
            assert item["origin"] == ORIGIN_KNOWLEDGE
            assert item["kind"] == "long_term"
            assert item["key"] == "发货偏好"
            assert item["content"] == "默认 DHL 3日达"

            recalled = await facade.recall_business(user, "发货偏好")
            assert recalled is not None
            assert recalled["origin"] == ORIGIN_KNOWLEDGE
            assert recalled["content"] == "默认 DHL 3日达"

    asyncio.run(_run())


# ============================================================================
# 会话记忆（agent）
# ============================================================================


def test_agent_memory_roundtrip():
    """写入会话记忆后可召回，且标记 origin=agent。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            item = await facade.remember_agent(
                user, agent_id="emp-001", role="user", content="帮我跟进德国客户"
            )
            assert item["origin"] == ORIGIN_AGENT
            assert item["key"] == "emp-001"
            assert item["content"] == "帮我跟进德国客户"
            assert item["kind"] in ("short_term", "medium_term", "long_term", "core")

            rows = await facade.recall_agent(user, "emp-001")
            assert len(rows) == 1
            assert rows[0]["origin"] == ORIGIN_AGENT
            assert rows[0]["content"] == "帮我跟进德国客户"

    asyncio.run(_run())


def test_recall_agent_messages_structure():
    """recall_agent_messages 输出可直接注入 LLM 的消息列表。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            await facade.remember_agent(
                user, agent_id="emp-002", role="user", content="查一下供应商交期"
            )
            await facade.remember_agent(
                user, agent_id="emp-002", role="assistant", content="交期为 15 天"
            )

            messages = await facade.recall_agent_messages(user, "emp-002")
            assert len(messages) == 3  # 1 system hint + 2 条记忆
            assert messages[0]["role"] == "system"
            assert messages[1] == {"role": "user", "content": "查一下供应商交期"}
            assert messages[2] == {"role": "assistant", "content": "交期为 15 天"}

    asyncio.run(_run())


# ============================================================================
# 统一列表
# ============================================================================


def test_list_all_merges_both_origins():
    """list_all 合并双系统记忆并标记 origin。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            await facade.remember_business(user, key="公司名称", value="鎏灏科技")
            await facade.remember_agent(
                user, agent_id="emp-001", role="user", content="跟进德国客户"
            )

            items = await facade.list_all(user)
            origins = {i["origin"] for i in items}
            assert origins == {ORIGIN_KNOWLEDGE, ORIGIN_AGENT}
            # 统一字段都存在
            for item in items:
                assert set(item) >= {
                    "id", "origin", "kind", "key", "content",
                    "importance", "is_core", "created_at", "meta",
                }

    asyncio.run(_run())


def test_list_all_kind_filter_cross_system():
    """kind=long_term 同时过滤两套系统。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            await facade.remember_business(
                user, key="长期规则", value="报价需老板审批", memory_type=MemoryType.LONG_TERM
            )
            await facade.remember_business(
                user, key="临时备注", value="会话内有效", memory_type=MemoryType.SHORT_TERM
            )
            # importance=0.9 → core 级
            await facade.remember_agent(
                user, agent_id="emp-001", role="assistant",
                content="最终决策：采用方案A", importance=0.9,
            )
            # 默认重要性 → short_term
            await facade.remember_agent(
                user, agent_id="emp-001", role="user", content="普通对话"
            )

            items = await facade.list_all(user, kind="long_term")
            kinds = {i["kind"] for i in items}
            assert kinds == {"long_term"}
            contents = {i["content"] for i in items}
            assert "报价需老板审批" in contents  # knowledge long_term
            # agent 侧 core 不在 long_term 过滤内
            assert "最终决策：采用方案A" not in contents
            assert "临时备注" not in contents
            assert "普通对话" not in contents

    asyncio.run(_run())


def test_list_agent_only_without_knowledge_permission():
    """无 KNOWLEDGE_READ 权限的用户只查会话记忆（origin=agent）不受阻。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            no_perm = create_test_user(user_id=99, is_superuser=False)

            await facade.remember_agent(
                no_perm, agent_id="emp-003", role="user", content="我的会话记忆"
            )
            items = await facade.list_all(no_perm, origin=ORIGIN_AGENT)
            assert len(items) == 1
            assert items[0]["content"] == "我的会话记忆"

    asyncio.run(_run())


def test_list_all_without_permission_denied():
    """无 KNOWLEDGE_READ 权限的用户合并查询（含业务记忆）被拒绝。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            no_perm = create_test_user(user_id=99, is_superuser=False)

            with pytest.raises(PermissionDeniedError):
                await facade.list_all(no_perm)

    asyncio.run(_run())


# ============================================================================
# 删除路由
# ============================================================================


def test_delete_routes_by_origin():
    """delete 按 origin 路由：业务记忆走 MemoryService，会话记忆直删。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            biz = await facade.remember_business(user, key="待删", value="v1")
            ag = await facade.remember_agent(
                user, agent_id="emp-001", role="user", content="待删会话"
            )

            r1 = await facade.delete(user, ORIGIN_KNOWLEDGE, biz["id"])
            assert r1["ok"] is True
            r2 = await facade.delete(user, ORIGIN_AGENT, ag["id"])
            assert r2["ok"] is True

            # 均已删除
            assert await facade.recall_business(user, "待删") is None
            rows = await facade.recall_agent(user, "emp-001")
            assert rows == []

    asyncio.run(_run())


def test_delete_agent_not_found():
    """删除不存在的会话记忆 → NotFoundError。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            with pytest.raises(NotFoundError):
                await facade.delete(user, ORIGIN_AGENT, "999999")

    asyncio.run(_run())


def test_delete_agent_other_user_forbidden():
    """非超管删除他人会话记忆 → PermissionDeniedError。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            owner = create_test_user(user_id=1)
            other = create_test_user(user_id=88, is_superuser=False)

            item = await facade.remember_agent(
                owner, agent_id="emp-001", role="user", content="他人记忆"
            )
            with pytest.raises(PermissionDeniedError):
                await facade.delete(other, ORIGIN_AGENT, item["id"])

    asyncio.run(_run())


def test_delete_agent_superuser_can_delete_others():
    """超管（老板）可删除他人的会话记忆。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            owner = create_test_user(user_id=1)
            boss = create_test_user(user_id=2, is_superuser=True)

            item = await facade.remember_agent(
                owner, agent_id="emp-001", role="user", content="下属记忆"
            )
            result = await facade.delete(boss, ORIGIN_AGENT, item["id"])
            assert result["ok"] is True

    asyncio.run(_run())


# ============================================================================
# 核心标记
# ============================================================================


def test_mark_agent_core():
    """mark_agent_core 标记永久保留并校验归属。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            item = await facade.remember_agent(
                user, agent_id="emp-001", role="assistant", content="关键决策：涨价 5%"
            )
            updated = await facade.mark_agent_core(user, item["id"], is_core=True)
            assert updated["is_core"] is True
            assert updated["kind"] == "core"

            # 数据库层面验证
            stmt = select(AgentMemoryModel).where(
                AgentMemoryModel.id == int(item["id"])
            )
            model = (await session.execute(stmt)).scalar_one()
            assert model.is_core is True
            assert model.expires_at is None

            # 他人不可标记
            other = create_test_user(user_id=77, is_superuser=False)
            with pytest.raises(PermissionDeniedError):
                await facade.mark_agent_core(other, item["id"], is_core=False)

    asyncio.run(_run())


# ============================================================================
# 统计
# ============================================================================


def test_overview_counts_both_systems():
    """overview 返回双系统分级统计。"""

    async def _run():
        session_factory = await create_test_session()
        async with session_factory() as session:
            facade = _facade(session)
            user = create_test_user()

            await facade.remember_business(user, key="k1", value="v1")
            await facade.remember_business(
                user, key="k2", value="v2", memory_type=MemoryType.WORKING
            )
            await facade.remember_agent(
                user, agent_id="emp-001", role="user", content="普通"
            )
            await facade.remember_agent(
                user, agent_id="emp-001", role="assistant", content="重要结论", importance=0.9
            )

            stats = await facade.overview(user)
            assert stats["knowledge"]["total"] == 2
            assert stats["knowledge"]["long_term"] == 1
            assert stats["knowledge"]["working"] == 1
            assert stats["agent"]["total"] == 2
            assert stats["agent"]["core"] == 1
            assert stats["agent"]["medium_term"] == 1
            assert stats["total"] == 4

    asyncio.run(_run())
