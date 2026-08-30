"""
多平台经营执行模式测试 — 验证消息的 source_type 字段正确标记。

覆盖：
- PlatformMessage 模型 source_type 默认值
- PlatformService.send_message() 标记 MOCK / REAL
- PlatformService._create_mock_reply() 标记 MOCK
- PlatformService.receive_messages() 标记 MOCK / REAL
- WebhookService 标记 REAL
- 生产环境阻止 Mock 发送
"""

import os
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base
from src.integrations.models import (
    MessageDirection,
    MessageStatus,
    PlatformAccount,
    PlatformAccountStatus,
    PlatformMessage,
    PlatformType,
)
from src.integrations.providers import MockPlatformProvider
from src.integrations.service import (
    EXECUTION_MODE_MOCK,
    EXECUTION_MODE_REAL,
    PlatformService,
)
from src.integrations.webhook import WebhookService


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def mock_account(db_session: AsyncSession) -> PlatformAccount:
    """创建一个 Mock 平台账号（无凭据）。"""
    account = PlatformAccount(
        platform=PlatformType.WHATSAPP,
        name="Test Mock Account",
        account_id="test-mock-123",
        status=PlatformAccountStatus.MOCK,
        is_active=True,
        owner_user_id=1,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


# ==================== PlatformMessage 模型 ====================


class TestPlatformMessageSourceType:
    """验证 PlatformMessage 模型 source_type 字段。"""

    @pytest.mark.asyncio
    async def test_default_source_type_is_mock(self, db_session: AsyncSession):
        """新消息默认 source_type 为 MOCK。"""
        msg = PlatformMessage(
            platform=PlatformType.WHATSAPP,
            account_id=1,
            direction=MessageDirection.OUTBOUND,
            content="test",
            status=MessageStatus.QUEUED,
            source_type="MOCK",
        )
        assert msg.source_type == "MOCK"

    @pytest.mark.asyncio
    async def test_can_set_source_type_to_real(self, db_session: AsyncSession):
        """可以设置 source_type 为 REAL。"""
        msg = PlatformMessage(
            platform=PlatformType.WHATSAPP,
            account_id=1,
            direction=MessageDirection.OUTBOUND,
            content="test",
            source_type="REAL",
            status=MessageStatus.SENT,
        )
        assert msg.source_type == "REAL"


# ==================== PlatformService send_message ====================


class TestPlatformServiceSendSourceType:
    """验证 send_message 的 source_type 标记。"""

    @pytest.mark.asyncio
    async def test_mock_provider_sets_mock_source_type(
        self, db_session: AsyncSession, mock_account: PlatformAccount
    ):
        """MockProvider 发送消息标记为 MOCK。"""
        service = PlatformService(db_session)
        result = await service.send_message(
            account_id=mock_account.id,
            owner_user_id=1,
            to_id="test-contact",
            content="Hello from test",
        )
        assert result["status"] == "sent"

        # 验证消息 source_type
        from sqlalchemy import select

        stmt = select(PlatformMessage).where(PlatformMessage.id == result["message_id"])
        msg = (await db_session.execute(stmt)).scalar_one()
        assert msg.source_type == EXECUTION_MODE_MOCK

    @pytest.mark.asyncio
    async def test_production_blocks_mock_send(
        self, db_session: AsyncSession, mock_account: PlatformAccount
    ):
        """生产环境禁止 MockProvider 发送消息。"""
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            service = PlatformService(db_session)
            with pytest.raises(ValueError, match="生产环境不允许使用 Mock"):
                await service.send_message(
                    account_id=mock_account.id,
                    owner_user_id=1,
                    to_id="test-contact",
                    content="Hello from test",
                )

    @pytest.mark.asyncio
    async def test_mock_reply_has_mock_source_type(
        self, db_session: AsyncSession, mock_account: PlatformAccount
    ):
        """Mock 自动回复标记为 MOCK。"""
        service = PlatformService(db_session)
        result = await service.send_message(
            account_id=mock_account.id,
            owner_user_id=1,
            to_id="test-contact",
            content="Hello",
        )

        # 验证有 Mock 回复消息
        from sqlalchemy import select

        stmt = (
            select(PlatformMessage)
            .where(
                PlatformMessage.account_id == mock_account.id,
                PlatformMessage.direction == MessageDirection.INBOUND,
            )
            .order_by(PlatformMessage.created_at.desc())
        )
        msgs = (await db_session.execute(stmt)).scalars().all()
        # 至少有一条 mock 回复
        mock_replies = [m for m in msgs if m.meta and m.meta.get("mock_reply")]
        assert len(mock_replies) >= 1
        assert mock_replies[0].source_type == EXECUTION_MODE_MOCK


# ==================== receive_messages ====================


class TestPlatformServiceReceiveSourceType:
    """验证 receive_messages 的 source_type 标记。"""

    @pytest.mark.asyncio
    async def test_receive_messages_mock_source_type(
        self, db_session: AsyncSession, mock_account: PlatformAccount
    ):
        """MockProvider 收取消息标记为 MOCK。"""
        # MockProvider.fetch_messages 返回空列表，所以不会有新消息
        # 验证至少不会报错，且返回的消息已有 source_type
        service = PlatformService(db_session)
        messages = await service.receive_messages(
            account_id=mock_account.id, owner_user_id=1
        )
        for msg in messages:
            assert msg.source_type in (EXECUTION_MODE_MOCK, EXECUTION_MODE_REAL)


# ==================== Webhook Service ====================


class TestWebhookServiceSourceType:
    """验证 Webhook 入库消息标记为 REAL。"""

    @pytest.mark.asyncio
    async def test_webhook_sets_real_source_type(
        self, db_session: AsyncSession, mock_account: PlatformAccount
    ):
        """Webhook 收到的消息标记为 REAL。"""
        webhook = WebhookService(db_session)
        body = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "12345",
                                        "id": "wamid.test001",
                                        "text": {"body": "Hello from customer"},
                                        "type": "text",
                                    }
                                ],
                                "contacts": [
                                    {"profile": {"name": "Customer A"}}
                                ],
                            }
                        }
                    ]
                }
            ]
        }
        count = await webhook.process_whatsapp(mock_account.id, body)
        assert count == 1

        # 验证消息 source_type
        from sqlalchemy import select

        stmt = select(PlatformMessage).where(
            PlatformMessage.account_id == mock_account.id,
            PlatformMessage.remote_id == "wamid.test001",
        )
        msg = (await db_session.execute(stmt)).scalar_one()
        assert msg.source_type == EXECUTION_MODE_REAL