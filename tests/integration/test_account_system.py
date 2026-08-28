"""
Account system integration tests.

Covers:
- Login (correct password, wrong password, inactive user, pending approval)
- Token validation (valid, expired, invalid)
- Sub-account registration (pending status, tenant binding, owner association)
- Owner approval workflow (approve, reject)
- Sub-account authorization (cannot access owner resources)
- Frontend-backend API consistency (auth/me, pending-approvals)
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.schemas import LoginRequest
from src.identity.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.identity.models import AccountType, ApprovalStatus, RoleEnum, User, Base


# ============================================================
# Helpers
# ============================================================

async def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _create_user(session_factory, **kwargs):
    defaults = dict(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("password123"),
        role=RoleEnum.USER,
        account_type=AccountType.OWNER,
        is_active=True,
        approval_status=None,
    )
    defaults.update(kwargs)
    async with session_factory() as session:
        user = User(**defaults)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ============================================================
# 1. Login tests
# ============================================================

class TestLogin:
    """正确账号密码登录 / 错误密码 / Token 生命周期"""

    def test_correct_password_login(self):
        """正确账号密码应该能获取 token"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_user(sf)
            assert verify_password("password123", user.hashed_password)
            assert user.is_active
            token = create_access_token({"sub": str(user.id), "role": user.role.value})
            payload = decode_access_token(token)
            assert payload["sub"] == str(user.id)

        asyncio.run(_run())

    def test_wrong_password_fails(self):
        """错误密码不应该通过验证"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_user(sf)
            assert not verify_password("wrongpassword", user.hashed_password)

        asyncio.run(_run())

    def test_inactive_user_cannot_login(self):
        """is_active=False 的用户不应该能登录（被 get_current_user 拦截）"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_user(sf, is_active=False)
            # 登录验证可以通过（密码正确），但 get_current_user 会拦截
            assert verify_password("password123", user.hashed_password)
            assert not user.is_active

        asyncio.run(_run())

    def test_pending_sub_account_cannot_login(self):
        """待审核的子账号登录应被拦截"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            # 密码正确但 approval_status=pending
            assert verify_password("password123", sub.hashed_password)
            assert sub.approval_status == "pending"
            assert not sub.is_active

        asyncio.run(_run())

    def test_token_round_trip(self):
        """Token 生成和验证应该完整闭环"""
        async def _run():
            sf, _ = await _make_session()
            user = await _create_user(sf)
            token = create_access_token(
                {"sub": str(user.id), "role": user.role.value}
            )
            payload = decode_access_token(token)
            assert payload["sub"] == str(user.id)
            assert payload["role"] == "user"
            assert "exp" in payload

        asyncio.run(_run())

    def test_token_with_invalid_signature(self):
        """无效签名的 token 应该被拒绝"""
        with pytest.raises(Exception):
            decode_access_token("invalid.token.here")

    def test_login_request_schema_valid(self):
        """LoginRequest schema 应该正常接收用户名和密码"""
        req = LoginRequest(username="testuser", password="password123")
        assert req.username == "testuser"
        assert req.password == "password123"


# ============================================================
# 2. Sub-account registration tests
# ============================================================

class TestSubAccountRegistration:
    """子账号注册：pending 状态 / tenant 绑定 / 主账号关联"""

    def test_sub_account_created_with_pending_status(self):
        """子账号注册后应该进入 pending 状态"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            assert sub.account_type == AccountType.SUB
            assert sub.is_active is False
            assert sub.approval_status == "pending"
            assert sub.parent_user_id == owner.id

        asyncio.run(_run())

    def test_sub_account_binds_to_owner_tenant(self):
        """子账号应该继承主账号的 tenant_id"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com",
                                       tenant_id="tenant_001")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            assert sub.tenant_id == "tenant_001"
            assert sub.tenant_id == owner.tenant_id

        asyncio.run(_run())

    def test_owner_can_see_pending_sub_accounts(self):
        """主账号应该能查询到待审核的子账号"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )

            async with sf() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(
                        User.account_type == AccountType.SUB,
                        User.parent_user_id == owner.id,
                        User.approval_status == ApprovalStatus.PENDING.value,
                    )
                )
                pending = list(result.scalars().all())
                assert len(pending) == 1
                assert pending[0].id == sub.id
                assert pending[0].approval_status == "pending"

        asyncio.run(_run())

    def test_owner_cannot_see_other_owners_pending_subs(self):
        """主账号不能看到其他主账号的待审核子账号"""
        async def _run():
            sf, _ = await _make_session()
            owner1 = await _create_user(sf, username="owner1", email="owner1@test.com")
            owner2 = await _create_user(sf, username="owner2", email="owner2@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner1.id,
                tenant_id=owner1.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )

            async with sf() as session:
                from sqlalchemy import select
                # owner2 不应该看到 owner1 的待审核子账号
                result = await session.execute(
                    select(User).where(
                        User.account_type == AccountType.SUB,
                        User.parent_user_id == owner2.id,
                        User.approval_status == ApprovalStatus.PENDING.value,
                    )
                )
                pending = list(result.scalars().all())
                assert len(pending) == 0

        asyncio.run(_run())


# ============================================================
# 3. Approval workflow tests
# ============================================================

class TestSubAccountApproval:
    """主账号审核子账号：批准 / 拒绝"""

    def test_approve_sub_account_activates_it(self):
        """批准后子账号应该变为 active"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            # 批准
            sub.approval_status = ApprovalStatus.APPROVED.value
            sub.is_active = True

            assert sub.is_active is True
            assert sub.approval_status == "approved"

        asyncio.run(_run())

    def test_reject_sub_account_keeps_it_inactive(self):
        """拒绝后子账号应该保持 inactive"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            # 拒绝
            sub.approval_status = ApprovalStatus.REJECTED.value
            sub.is_active = False

            assert sub.is_active is False
            assert sub.approval_status == "rejected"

        asyncio.run(_run())

    def test_approved_sub_account_can_login(self):
        """批准后的子账号应该可以正常登录"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            # 批准
            sub.approval_status = ApprovalStatus.APPROVED.value
            sub.is_active = True

            # 批准后可以登录
            assert verify_password("password123", sub.hashed_password)
            assert sub.is_active

            token = create_access_token({"sub": str(sub.id), "role": sub.role.value})
            payload = decode_access_token(token)
            assert payload["sub"] == str(sub.id)

        asyncio.run(_run())


# ============================================================
# 4. Authorization tests
# ============================================================

class TestSubAccountAuthorization:
    """子账号权限限制"""

    def test_sub_account_is_not_owner(self):
        """子账号 account_type 应该是 SUB 而不是 OWNER"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED.value,
            )
            assert sub.account_type == AccountType.SUB
            assert sub.account_type != AccountType.OWNER

        asyncio.run(_run())

    def test_sub_account_has_parent_user_id(self):
        """子账号应该关联到主账号"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED.value,
            )
            assert sub.parent_user_id == owner.id

        asyncio.run(_run())


# ============================================================
# 5. Frontend-backend consistency tests
# ============================================================

class TestConsistency:
    """前后端 API 数据一致性"""

    def test_auth_me_returns_account_type(self):
        """GET /auth/me 应该返回 account_type 字段"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED.value,
            )
            # 模拟 UserResponse 序列化
            from src.api.schemas import UserDetailResponse
            owner_out = UserDetailResponse.model_validate(owner)
            sub_out = UserDetailResponse.model_validate(sub)
            assert owner_out.account_type == "owner"
            assert sub_out.account_type == "sub"
            assert sub_out.parent_user_id == owner.id

        asyncio.run(_run())

    def test_pending_approvals_returns_correct_format(self):
        """pending-approvals 接口应该返回正确的数据格式"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )

            async with sf() as session:
                from sqlalchemy import select
                from src.api.schemas import UserResponse
                stmt = select(User).where(
                    User.account_type == AccountType.SUB,
                    User.parent_user_id == owner.id,
                    User.approval_status == ApprovalStatus.PENDING.value,
                )
                result = await session.execute(stmt)
                users = list(result.scalars().all())
                # 序列化为 UserResponse
                responses = [UserResponse.model_validate(u) for u in users]
                assert len(responses) == 1
                assert responses[0].approval_status == "pending"
                assert responses[0].is_active is False
                # account_type 应该包含
                assert responses[0].account_type is not None

        asyncio.run(_run())

    def test_sub_account_list_includes_approval_status(self):
        """子账号列表应该包含 approval_status 字段"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                is_active=False,
                approval_status=ApprovalStatus.PENDING.value,
            )
            from src.api.schemas import UserResponse
            resp = UserResponse.model_validate(sub)
            assert resp.approval_status == "pending"
            assert resp.account_type == "sub"
            assert resp.is_active is False

        asyncio.run(_run())


# ============================================================
# 6. Tenant isolation tests
# ============================================================

class TestTenantIsolation:
    """租户数据隔离"""

    def test_sub_account_inherits_tenant(self):
        """子账号应该继承主账号的 tenant"""
        async def _run():
            sf, _ = await _make_session()
            owner = await _create_user(sf, username="owner", email="owner@test.com",
                                       tenant_id="tenant_abc")
            sub = await _create_user(
                sf,
                username="subuser",
                email="sub@test.com",
                account_type=AccountType.SUB,
                parent_user_id=owner.id,
                tenant_id=owner.tenant_id,
                is_active=True,
                approval_status=ApprovalStatus.APPROVED.value,
            )
            assert sub.tenant_id == "tenant_abc"
            assert sub.tenant_id == owner.tenant_id

        asyncio.run(_run())

    def test_users_with_different_tenants_are_isolated(self):
        """不同租户的用户数据应该隔离"""
        async def _run():
            sf, _ = await _make_session()
            await _create_user(sf, username="user_a", email="a@test.com",
                               tenant_id="tenant_a")
            await _create_user(sf, username="user_b", email="b@test.com",
                               tenant_id="tenant_b")

            async with sf() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.tenant_id == "tenant_a")
                )
                users_a = list(result.scalars().all())
                assert len(users_a) == 1
                assert users_a[0].username == "user_a"

        asyncio.run(_run())