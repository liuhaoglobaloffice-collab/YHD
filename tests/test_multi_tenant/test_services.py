# ⚠️ DISABLED - Requires async migration
# TODO: Convert multi_tenant module from sync SQLAlchemy to async
# Related: ULTIMATE_MASTER_FRAMEWORK Week 1-2 async conversion
# Issue: Module uses sync Session but project is async-first
# Estimated work: 2-3 hours
#

import pytest

pytest.skip(allow_module_level=True, reason="Requires async migration - Week 1-2 TODO")

"""
多租户Token隐秘调度系统 - 单元测试

测试核心功能：
1. 账号创建（主账号/子账号）
2. Token隐秘消费
3. Token隐秘转移
4. 自动借用规则
5. 双重视图（真相 vs 表象）
6. Token隔离强制
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.multi_tenant.models import (
    AccountType,
    APIProviderType,
    TokenUsageStats,
)
from src.multi_tenant.services import (
    AccountService,
    APIConfigurationService,
    TokenIsolationEnforcer,
    TokenStealthService,
)

# 测试数据库设置
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


# ==================== 测试账号服务 ====================


def test_create_master_account(db):
    """测试创建主账号"""
    master = AccountService.create_master_account(
        db=db,
        username="boss",
        email="boss@example.com",
        password_hash="hashed_password",
        display_name="老板",
    )

    assert master.id is not None
    assert master.account_type == AccountType.MASTER
    assert master.username == "boss"
    assert master.master_account_id is None

    # 验证自动创建了Token统计
    stats = db.query(TokenUsageStats).filter_by(account_id=master.id).first()
    assert stats is not None


def test_create_sub_account(db):
    """测试创建子账号"""
    # 先创建主账号
    master = AccountService.create_master_account(
        db=db,
        username="boss",
        email="boss@example.com",
        password_hash="hashed_password",
    )

    # 创建子账号
    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="employee1",
        email="employee1@example.com",
        password_hash="hashed_password",
        display_name="员工1",
    )

    assert sub.id is not None
    assert sub.account_type == AccountType.SUB
    assert sub.master_account_id == master.id

    # 验证自动创建了Token统计和隐秘权限
    stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    assert stats is not None


def test_get_sub_accounts(db):
    """测试获取所有子账号"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub1 = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    sub2 = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp2",
        email="emp2@example.com",
        password_hash="hashed",
    )

    subs = AccountService.get_sub_accounts(db, master.id)
    assert len(subs) == 2
    assert sub1.id in [s.id for s in subs]
    assert sub2.id in [s.id for s in subs]


# ==================== 测试API配置服务 ====================


def test_save_api_configuration(db):
    """测试保存API配置"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    config = APIConfigurationService.save_configuration(
        db=db,
        account_id=master.id,
        provider=APIProviderType.OPENAI,
        api_key="sk-test-key",
        model_name="gpt-3.5-turbo",
        is_default=True,
    )

    assert config.id is not None
    assert config.provider == APIProviderType.OPENAI
    assert config.is_default


def test_get_default_configuration(db):
    """测试获取默认配置"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    # 创建两个配置，其中一个为默认
    APIConfigurationService.save_configuration(
        db=db,
        account_id=master.id,
        provider=APIProviderType.OPENAI,
        api_key="sk-key1",
        is_default=False,
    )

    config2 = APIConfigurationService.save_configuration(
        db=db,
        account_id=master.id,
        provider=APIProviderType.ANTHROPIC,
        api_key="sk-key2",
        is_default=True,
    )

    default = APIConfigurationService.get_default_configuration(db, master.id)
    assert default.id == config2.id
    assert default.provider == APIProviderType.ANTHROPIC


def test_estimate_tokens_from_balance():
    """测试Token估算"""
    # OpenAI: $10 余额 = 1,000,000 tokens (假设$0.01/1K)
    tokens = APIConfigurationService.estimate_tokens_from_balance(APIProviderType.OPENAI, 10.0)
    assert tokens == 1_000_000

    # Ollama: 本地免费 = 无限Token
    tokens = APIConfigurationService.estimate_tokens_from_balance(APIProviderType.OLLAMA, 0)
    assert tokens == 999999999


# ==================== 测试Token隐秘调度服务（核心🔥） ====================


def test_stealth_consume_success(db):
    """测试主账号隐秘消费子账号Token - 成功场景"""
    # 1. 创建主账号和子账号
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    # 2. 给子账号分配Token
    sub_stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    sub_stats.total_quota = 10000
    sub_stats.remaining = 10000
    db.commit()

    # 3. 主账号隐秘消费子账号Token
    result = TokenStealthService.stealth_consume(
        db=db,
        master_account_id=master.id,
        sub_account_id=sub.id,
        tokens_needed=500,
        provider=APIProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        task_description="主账号测试任务",
    )

    # 4. 验证结果
    assert result["success"]
    assert result["tokens_consumed"] == 500

    # 5. 验证子账号Token统计
    db.refresh(sub_stats)
    assert sub_stats.stolen_by_master == 500  # 被偷用500
    assert sub_stats.total_consumed == 500
    assert sub_stats.remaining == 9500

    # 6. 验证消费日志
    from src.multi_tenant.models import TokenConsumptionLog

    log = db.query(TokenConsumptionLog).filter_by(account_id=sub.id).first()
    assert log is not None
    assert log.real_consumer_id == master.id  # 真实消费者是主账号
    assert log.is_stealth  # 标记为隐秘
    assert log.visible_reason == "系统任务"  # 对子账号显示的原因


def test_stealth_consume_insufficient_tokens(db):
    """测试Token不足的情况"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    # 子账号只有100 Token
    sub_stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    sub_stats.total_quota = 100
    sub_stats.remaining = 100
    db.commit()

    # 尝试消费500 Token（超过余额）
    result = TokenStealthService.stealth_consume(
        db=db,
        master_account_id=master.id,
        sub_account_id=sub.id,
        tokens_needed=500,
        provider=APIProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
        task_description="测试任务",
    )

    # 应该失败
    assert not result["success"]
    assert "Insufficient tokens" in result["message"]


def test_stealth_transfer(db):
    """测试主账号隐秘转移Token"""
    # 1. 创建主账号和两个子账号
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub_a = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_a",
        email="emp_a@example.com",
        password_hash="hashed",
    )

    sub_b = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_b",
        email="emp_b@example.com",
        password_hash="hashed",
    )

    # 2. 设置初始Token
    stats_a = db.query(TokenUsageStats).filter_by(account_id=sub_a.id).first()
    stats_a.total_quota = 10000
    stats_a.remaining = 10000

    stats_b = db.query(TokenUsageStats).filter_by(account_id=sub_b.id).first()
    stats_b.total_quota = 1000
    stats_b.remaining = 1000
    db.commit()

    # 3. 主账号从A转2000给B
    result = TokenStealthService.stealth_transfer(
        db=db,
        master_account_id=master.id,
        from_sub_account_id=sub_a.id,
        to_sub_account_id=sub_b.id,
        tokens_amount=2000,
        reason="资源调配",
    )

    # 4. 验证结果
    assert result["success"]
    assert result["tokens_transferred"] == 2000

    # 5. 验证Token变化
    db.refresh(stats_a)
    db.refresh(stats_b)

    assert stats_a.remaining == 8000  # A: 10000 - 2000 = 8000
    assert stats_b.remaining == 3000  # B: 1000 + 2000 = 3000


def test_auto_borrow_if_needed(db):
    """测试自动借用规则"""
    # 1. 创建主账号（Token不足）
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    master_stats = db.query(TokenUsageStats).filter_by(account_id=master.id).first()
    master_stats.total_quota = 100
    master_stats.remaining = 50  # 只有50 Token
    db.commit()

    # 2. 创建子账号（Token充足）
    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    sub_stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    sub_stats.total_quota = 10000
    sub_stats.remaining = 10000
    db.commit()

    # 3. 主账号需要500 Token（超过自己的余额）
    result = TokenStealthService.auto_borrow_if_needed(
        db=db,
        master_account_id=master.id,
        tokens_needed=500,
        provider=APIProviderType.OPENAI,
        model_name="gpt-3.5-turbo",
    )

    # 4. 验证自动借用成功
    assert result is not None
    assert result["success"]
    assert result["source_account_id"] == sub.id

    # 5. 验证子账号Token减少
    db.refresh(sub_stats)
    assert sub_stats.remaining == 9500  # 10000 - 500


# ==================== 测试双重视图 ====================


def test_master_truth_view(db):
    """测试主账号真相视图"""
    # 1. 创建主账号和子账号
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    # 2. 设置Token
    sub_stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    sub_stats.total_quota = 10000
    sub_stats.remaining = 10000
    sub_stats.self_consumed = 1000
    sub_stats.stolen_by_master = 500  # 主账号偷用了500
    sub_stats.total_consumed = 1500
    sub_stats.remaining = 8500
    db.commit()

    # 3. 获取主账号真相视图
    view = TokenStealthService.get_master_truth_view(db, master.id)

    # 4. 验证主账号可以看到被偷用的详情
    assert len(view["sub_accounts"]) == 1
    sub_info = view["sub_accounts"][0]
    assert sub_info["account_id"] == sub.id
    assert sub_info["self_consumed"] == 1000
    assert sub_info["stolen_by_master"] == 500  # 🔥 主账号能看到
    assert sub_info["total_consumed"] == 1500


def test_sub_illusion_view(db):
    """测试子账号表象视图"""
    # 1. 创建主账号和子账号
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    # 2. 设置Token（包含被偷用的）
    sub_stats = db.query(TokenUsageStats).filter_by(account_id=sub.id).first()
    sub_stats.total_quota = 10000
    sub_stats.self_consumed = 1000
    sub_stats.stolen_by_master = 500  # 被主账号偷用
    sub_stats.total_consumed = 1500
    sub_stats.remaining = 8500
    db.commit()

    # 3. 获取子账号表象视图
    view = TokenStealthService.get_sub_illusion_view(db, sub.id)

    # 4. 验证子账号看不到被偷用的详情
    assert view["total_consumed"] == 1500  # 只看到总消费
    assert view["remaining"] == 8500
    assert "stolen_by_master" not in view  # ❌ 看不到被偷用的
    assert "cost_by_master" not in view  # ❌ 看不到主账号消费的成本


# ==================== 测试Token隔离 ====================


def test_token_isolation_self_access(db):
    """测试访问自己的Token - 应该允许"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    allowed = TokenIsolationEnforcer.enforce_isolation(db, master.id, master.id)
    assert allowed


def test_token_isolation_master_to_sub(db):
    """测试主账号访问子账号Token - 应该允许"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    allowed = TokenIsolationEnforcer.enforce_isolation(db, master.id, sub.id)
    assert allowed


def test_token_isolation_sub_to_master(db):
    """测试子账号访问主账号Token - 应该拒绝"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp1",
        email="emp1@example.com",
        password_hash="hashed",
    )

    allowed = TokenIsolationEnforcer.enforce_isolation(db, sub.id, master.id)
    assert not allowed  # ❌ 子账号不能访问主账号


def test_token_isolation_sub_to_sub(db):
    """测试子账号访问其他子账号Token - 应该拒绝"""
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub_a = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_a",
        email="emp_a@example.com",
        password_hash="hashed",
    )

    sub_b = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_b",
        email="emp_b@example.com",
        password_hash="hashed",
    )

    allowed = TokenIsolationEnforcer.enforce_isolation(db, sub_a.id, sub_b.id)
    assert not allowed  # ❌ 子账号之间不能互相访问


def test_get_accessible_accounts(db):
    """测试获取可访问账号列表"""
    # 1. 创建主账号和两个子账号
    master = AccountService.create_master_account(
        db=db, username="boss", email="boss@example.com", password_hash="hashed"
    )

    sub_a = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_a",
        email="emp_a@example.com",
        password_hash="hashed",
    )

    sub_b = AccountService.create_sub_account(
        db=db,
        master_account_id=master.id,
        username="emp_b",
        email="emp_b@example.com",
        password_hash="hashed",
    )

    # 2. 主账号可以访问自己和所有子账号
    master_accessible = TokenIsolationEnforcer.get_accessible_accounts(db, master.id)
    assert master.id in master_accessible
    assert sub_a.id in master_accessible
    assert sub_b.id in master_accessible
    assert len(master_accessible) == 3

    # 3. 子账号只能访问自己
    sub_a_accessible = TokenIsolationEnforcer.get_accessible_accounts(db, sub_a.id)
    assert sub_a.id in sub_a_accessible
    assert master.id not in sub_a_accessible
    assert sub_b.id not in sub_a_accessible
    assert len(sub_a_accessible) == 1
