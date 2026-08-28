"""
V4 预算拦截单元测试.

覆盖:
- CostTracker.check_budget(): 无限预算 / 预算内 / 超预算
- workforce._enforce_ai_budget(): 未设预算放行 / 预算内放行 / 超限抛 402

使用内存 SQLite（每次用例独立建库），不依赖外部服务。
"""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# 注册所有 ORM 模型到共享 metadata
import src.database.models  # noqa: F401
import src.identity.models  # noqa: F401
from src.ai.cost_tracker import CostTracker
from src.database.base import Base
from src.identity.models import AccountType, User


@pytest_asyncio.fixture
async def session():
    """内存 SQLite 会话：每次用例全新库表。"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


async def _mk_user(session, username: str, budget=None, account_type=AccountType.SUB) -> User:
    """创建测试用户（默认子账号，可指定月度 AI 预算）。"""
    user = User(
        username=username,
        email=f"{username}@test.local",
        hashed_password="x",
        account_type=account_type,
        ai_budget_monthly=budget,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ==================== CostTracker.check_budget ====================


@pytest.mark.asyncio
async def test_check_budget_unlimited_when_no_budget_set(session):
    """未设置预算（NULL）→ 始终放行。"""
    user = await _mk_user(session, "sub_no_budget", budget=None)
    check = await CostTracker(session).check_budget(user.id)
    assert check["allow"] is True
    assert check["budget"] is None
    assert check["over_budget"] is False


@pytest.mark.asyncio
async def test_check_budget_allows_within_limit(session):
    """预算充足 → 放行，并返回剩余量。"""
    user = await _mk_user(session, "sub_within", budget=10.0)
    await CostTracker(session).record(
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=1_000,
        output_tokens=500,
    )
    check = await CostTracker(session).check_budget(user.id)
    assert check["allow"] is True
    assert check["over_budget"] is False
    assert check["used_usd"] > 0  # 服务内按 4 位舍入记账，此处只校验发生过费用
    assert check["remaining_usd"] == pytest.approx(10.0 - check["used_usd"], abs=1e-4)
    assert check["calls"] == 1


@pytest.mark.asyncio
async def test_check_budget_blocks_over_limit(session):
    """当月成本超过预算 → 拦截（allow=False）。"""
    user = await _mk_user(session, "sub_over", budget=0.0001)
    # 成本 = (2000*0.15 + 1000*0.60)/1e6 = 0.0009 > 0.0001
    await CostTracker(session).record(
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=2_000,
        output_tokens=1_000,
    )
    check = await CostTracker(session).check_budget(user.id)
    assert check["allow"] is False
    assert check["over_budget"] is True
    assert check["budget"] == 0.0001
    assert check["remaining_usd"] < 0
    assert check["calls"] == 1


@pytest.mark.asyncio
async def test_check_budget_unknown_user_allows(session):
    """用户不存在 → 视为无预算不拦截（避免误伤未绑定账号）。"""
    check = await CostTracker(session).check_budget(999_999)
    assert check["allow"] is True
    assert check["budget"] is None


@pytest.mark.asyncio
async def test_check_budget_counts_full_month_not_day(session):
    """月度统计按自然月聚合：多次调用累加成本。"""
    user = await _mk_user(session, "sub_accumulate", budget=0.0005)
    for _ in range(3):
        await CostTracker(session).record(
            user_id=user.id,
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=1_000,
            output_tokens=500,
        )
    # 3 次调用累计成本 > 0.0005，必须被拦截
    check = await CostTracker(session).check_budget(user.id)
    assert check["calls"] == 3
    assert check["used_usd"] > 0.0005
    assert check["allow"] is False


# ==================== workforce._enforce_ai_budget ====================


@pytest.mark.asyncio
async def test_enforce_ai_budget_unlimited_passes(session):
    """未设预算的账号不被拦截。"""
    from src.api.routes.workforce import _enforce_ai_budget

    user = await _mk_user(session, "sub_no_budget_2", budget=None)
    # 不应抛异常
    await _enforce_ai_budget(session, user)


@pytest.mark.asyncio
async def test_enforce_ai_budget_within_limit_passes(session):
    """预算内的账号放行。"""
    from src.api.routes.workforce import _enforce_ai_budget

    user = await _mk_user(session, "sub_within_2", budget=10.0)
    await CostTracker(session).record(
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
    )
    await _enforce_ai_budget(session, user)


@pytest.mark.asyncio
async def test_enforce_ai_budget_over_raises_402(session):
    """超预算的账号被 402 拦截。"""
    from src.api.routes.workforce import _enforce_ai_budget

    user = await _mk_user(session, "sub_over_2", budget=0.0001)
    await CostTracker(session).record(
        user_id=user.id,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=2_000,
        output_tokens=1_000,
    )
    with pytest.raises(HTTPException) as exc_info:
        await _enforce_ai_budget(session, user)
    assert exc_info.value.status_code == 402
    assert "预算" in exc_info.value.detail


@pytest.mark.asyncio
async def test_enforce_ai_budget_owner_unlimited_by_default(session):
    """主账号未设预算默认放行（限制只作用于配置过预算的账号）。"""
    from src.api.routes.workforce import _enforce_ai_budget

    owner = await _mk_user(session, "owner_no_budget", budget=None, account_type=AccountType.OWNER)
    await _enforce_ai_budget(session, owner)


@pytest.mark.asyncio
async def test_all_users_queryable_via_session_for_budget(session):
    """回归：check_budget 基于 session.get 读取 User，被拦截账号仍在库中。"""
    user = await _mk_user(session, "sub_query_back", budget=0.0)
    result = await session.execute(select(User).where(User.id == user.id))
    assert result.scalar_one().ai_budget_monthly == 0.0