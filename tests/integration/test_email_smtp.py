"""SMTP 邮件发送集成测试 — EmailService + LeadService.send_lead_email。

覆盖：
- 未配置 SMTP → 诚实返回 NOT_CONFIGURED（不伪造发送成功）
- 已配置 + SMTP 正常 → source_type=REAL + message_id
- 已配置 + SMTP 失败 → source_type=FAILED + 错误记录
- 无效收件地址 → FAILED
- send_lead_email 成功/未配置均落盘 LeadActivity(type=email)
"""

from types import SimpleNamespace
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import smtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def _settings(configured: bool, use_ssl: bool = False):
    """构造可控的 Settings 替身。"""
    return SimpleNamespace(
        smtp_host="smtp.gmail.com" if configured else None,
        smtp_port=465 if use_ssl else 587,
        smtp_user="boss@example.com" if configured else None,
        smtp_password="app-password-16" if configured else None,
        smtp_from="boss@example.com" if configured else None,
        smtp_use_ssl=use_ssl,
    )


# ==================== EmailService 单元层 ====================


class TestEmailService:

    @pytest.mark.asyncio
    async def test_not_configured_returns_honestly(self):
        """未配置 SMTP → NOT_CONFIGURED，绝不伪造 sent。"""
        from src.integrations.email import EmailService

        svc = EmailService(settings=_settings(configured=False))
        assert svc.is_configured is False

        result = await svc.send_email("customer@us.com", "Hi", "Hello")

        assert result["source_type"] == "NOT_CONFIGURED"
        assert result["status"] == "not_configured"
        assert result["message_id"] is None
        assert "SMTP" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_address_fails_fast(self):
        """无效收件地址 → FAILED，不发起 SMTP 连接。"""
        from src.integrations.email import EmailService

        svc = EmailService(settings=_settings(configured=True))
        result = await svc.send_email("not-an-email", "Hi", "Hello")

        assert result["source_type"] == "FAILED"
        assert result["status"] == "failed"
        assert "无效" in result["error"]

    @pytest.mark.asyncio
    async def test_real_send_starttls(self, monkeypatch):
        """已配置 + STARTTLS 路径 → source_type=REAL + message_id。"""
        from src.integrations.email import EmailService

        sent = {}

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                sent["host"] = host
                sent["port"] = port

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def starttls(self):
                sent["starttls"] = True

            def login(self, user, password):
                sent["login"] = user

            def send_message(self, msg):
                sent["message_id"] = msg.get("Message-ID")
                sent["to"] = msg["To"]

        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        svc = EmailService(settings=_settings(configured=True))
        result = await svc.send_email("customer@us.com", "Quote", "Body here")

        assert result["source_type"] == "REAL"
        assert result["status"] == "sent"
        assert result["message_id"] == sent["message_id"]
        assert sent["host"] == "smtp.gmail.com"
        assert sent["port"] == 587
        assert sent["starttls"] is True
        assert sent["login"] == "boss@example.com"
        assert sent["to"] == "customer@us.com"

    @pytest.mark.asyncio
    async def test_real_send_ssl(self, monkeypatch):
        """SMTP_USE_SSL=true → 走 SMTP_SSL 且不调用 starttls。"""
        from src.integrations.email import EmailService

        calls = {}

        class FakeSMTPSSL:
            def __init__(self, host, port, timeout=None):
                calls["ssl"] = True

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def starttls(self):
                calls["starttls"] = True

            def login(self, user, password):
                pass

            def send_message(self, msg):
                calls["message_id"] = msg.get("Message-ID")

        monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTPSSL)
        svc = EmailService(settings=_settings(configured=True, use_ssl=True))
        result = await svc.send_email("customer@us.com", "Quote", "Body")

        assert result["source_type"] == "REAL"
        assert calls.get("ssl") is True
        assert "starttls" not in calls

    @pytest.mark.asyncio
    async def test_smtp_failure_recorded(self, monkeypatch):
        """SMTP 异常 → FAILED + 错误信息（不抛出，交给调用方落盘）。"""
        from src.integrations.email import EmailService

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def starttls(self):
                pass

            def login(self, user, password):
                raise smtplib.SMTPAuthenticationError(535, b"Bad credentials")

            def send_message(self, msg):
                raise AssertionError("login 失败后不应发送")

        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        svc = EmailService(settings=_settings(configured=True))
        result = await svc.send_email("customer@us.com", "Quote", "Body")

        assert result["source_type"] == "FAILED"
        assert result["status"] == "failed"
        assert "SMTPAuthenticationError" in result["error"]

    @pytest.mark.asyncio
    async def test_connection_error_recorded(self, monkeypatch):
        """网络连接失败（OSError）→ FAILED。"""
        from src.integrations.email import EmailService

        def boom(host, port, timeout=None):
            raise OSError("connection refused")

        monkeypatch.setattr(smtplib, "SMTP", boom)
        svc = EmailService(settings=_settings(configured=True))
        result = await svc.send_email("customer@us.com", "Quote", "Body")

        assert result["source_type"] == "FAILED"
        assert "connection refused" in result["error"]


# ==================== LeadService.send_lead_email 集成层 ====================


async def _create_user_and_lead(session: AsyncSession, email: str = "customer@us.com"):
    from src.crm.models import Lead, LeadSource
    from src.identity.models import AccountType, RoleEnum, User

    user = User(
        username="boss",
        email="boss@example.com",
        hashed_password="x" * 60,
        role=RoleEnum.ADMIN,
        account_type=AccountType.OWNER,
        is_active=True,
    )
    session.add(user)
    await session.flush()

    lead = Lead(
        source=LeadSource.GOOGLE,
        source_type="REAL",
        name="John",
        company="US Buyer Inc",
        country="USA",
        email=email,
        owner_user_id=user.id,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(user)
    await session.refresh(lead)
    return user, lead


class TestSendLeadEmail:

    @pytest.mark.asyncio
    async def test_send_success_persists_activity(self, db_session, monkeypatch):
        """真实发送成功 → LeadActivity 落盘，result 含 message_id。"""
        from src.crm.models import ActivityType, LeadActivity
        from src.crm.service import LeadService
        from src.integrations.email import EmailService

        user, lead = await _create_user_and_lead(db_session)

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def starttls(self):
                pass

            def login(self, u, p):
                pass

            def send_message(self, msg):
                pass

        monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
        service = LeadService(db_session)
        result = await service.send_lead_email(
            lead_id=lead.id,
            owner_user_id=user.id,
            subject="Quote for LED lights",
            body="Dear John, here is our quote.",
            email_service=EmailService(settings=_settings(configured=True)),
        )

        assert result["source_type"] == "REAL"
        assert result["status"] == "sent"
        assert result["message_id"]
        assert result["activity_id"]

        activity = (
            await db_session.execute(
                select(LeadActivity).where(LeadActivity.lead_id == lead.id)
            )
        ).scalars().one()
        assert activity.activity_type == ActivityType.EMAIL
        assert activity.result.startswith("sent, message_id=")
        assert "[REAL]" in activity.content

    @pytest.mark.asyncio
    async def test_not_configured_still_records_activity(self, db_session):
        """SMTP 未配置 → NOT_CONFIGURED + LeadActivity 仍落盘（诚实标记）。"""
        from src.crm.models import ActivityType, LeadActivity
        from src.crm.service import LeadService
        from src.integrations.email import EmailService

        user, lead = await _create_user_and_lead(db_session)
        service = LeadService(db_session)
        result = await service.send_lead_email(
            lead_id=lead.id,
            owner_user_id=user.id,
            subject="Follow up",
            body="Hello",
            email_service=EmailService(settings=_settings(configured=False)),
        )

        assert result["source_type"] == "NOT_CONFIGURED"
        assert result["status"] == "not_configured"

        activity = (
            await db_session.execute(
                select(LeadActivity).where(LeadActivity.lead_id == lead.id)
            )
        ).scalars().one()
        assert activity.activity_type == ActivityType.EMAIL
        assert "[NOT_CONFIGURED]" in activity.content
        assert "not_configured" in activity.result

    @pytest.mark.asyncio
    async def test_missing_lead_raises(self, db_session):
        """线索不存在 → ValueError（不静默伪造）。"""
        from src.crm.service import LeadService
        from src.integrations.email import EmailService

        service = LeadService(db_session)
        with pytest.raises(ValueError, match="线索不存在"):
            await service.send_lead_email(
                lead_id=99999,
                owner_user_id=1,
                subject="x",
                body="y",
                email_service=EmailService(settings=_settings(configured=False)),
            )

    @pytest.mark.asyncio
    async def test_send_failure_persists_failure_activity(self, db_session, monkeypatch):
        """SMTP 失败 → LeadActivity 记录失败原因（失败必须落盘）。"""
        from src.crm.models import LeadActivity
        from src.crm.service import LeadService
        from src.integrations.email import EmailService

        user, lead = await _create_user_and_lead(db_session)

        def boom(host, port, timeout=None):
            raise OSError("connection refused")

        monkeypatch.setattr(smtplib, "SMTP", boom)
        service = LeadService(db_session)
        result = await service.send_lead_email(
            lead_id=lead.id,
            owner_user_id=user.id,
            subject="Quote",
            body="Body",
            email_service=EmailService(settings=_settings(configured=True)),
        )

        assert result["source_type"] == "FAILED"
        activity = (
            await db_session.execute(
                select(LeadActivity).where(LeadActivity.lead_id == lead.id)
            )
        ).scalars().one()
        assert activity.result.startswith("failed:")
        assert "[FAILED]" in activity.content

    @pytest.mark.asyncio
    async def test_lead_without_email_fails_cleanly(self, db_session):
        """线索无邮箱 → FAILED（无效地址），活动仍记录。"""
        from src.crm.service import LeadService
        from src.integrations.email import EmailService

        user, lead = await _create_user_and_lead(db_session, email=None)
        service = LeadService(db_session)
        result = await service.send_lead_email(
            lead_id=lead.id,
            owner_user_id=user.id,
            subject="Hi",
            body="Hello",
            email_service=EmailService(settings=_settings(configured=True)),
        )

        assert result["source_type"] == "FAILED"
        assert "无效" in result["error"]
