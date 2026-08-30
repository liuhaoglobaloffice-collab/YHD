"""
S2 多平台接入 - 平台服务

负责平台账号管理、消息收发编排、联系人拉取。
未配置凭据的账号自动使用 Mock Provider（开发模式）。
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.base import PlatformProvider, registry
from src.core.encryption import decrypt_credentials, encrypt_credentials
from src.integrations.models import (
    MessageDirection,
    MessageStatus,
    PlatformAccount,
    PlatformAccountStatus,
    PlatformContact,
    PlatformMessage,
    PlatformType,
)
from src.integrations.providers import MockPlatformProvider
from src.integrations.translation import TranslationService

# 执行模式常量
EXECUTION_MODE_REAL = "REAL"
EXECUTION_MODE_MOCK = "MOCK"
EXECUTION_MODE_NOT_CONFIGURED = "NOT_CONFIGURED"

logger = logging.getLogger(__name__)

# Mock 自动回复语料（模拟对方回复，便于演示"发消息并收回复"）
_MOCK_REPLIES = [
    "Thank you for your message! We will review and get back to you soon.",
    "收到，我们稍后回复您。",
    "Thanks! Could you share more details about the product?",
    "已收到您的信息，感谢联系。",
]


class PlatformService:
    """平台接入服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.translator = TranslationService()

    # ==================== 账号管理 ====================

    def _get_provider(self, account: PlatformAccount) -> PlatformProvider:
        """获取平台 Provider，未配置凭据时回退到 Mock。"""
        provider_cls = registry.get_provider_class(account.platform.value)
        if provider_cls and account.credentials:
            # 解密凭据后传给 Provider
            decrypted = decrypt_credentials(account.credentials)
            return provider_cls(account, credentials=decrypted)
        return MockPlatformProvider(account)

    async def create_account(
        self,
        platform: str,
        name: str,
        account_id: str,
        credentials: Optional[Dict[str, Any]],
        owner_user_id: int,
        tenant_id: Optional[str] = None,
    ) -> PlatformAccount:
        """创建平台账号绑定。"""
        platform_enum = PlatformType(platform)

        # 同一平台同一账号ID去重
        existing = await self.session.execute(
            select(PlatformAccount).where(
                PlatformAccount.platform == platform_enum,
                PlatformAccount.account_id == account_id,
                PlatformAccount.owner_user_id == owner_user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该平台账号已存在")

        account = PlatformAccount(
            platform=platform_enum,
            name=name,
            account_id=account_id,
            credentials=encrypt_credentials(credentials) if credentials else None,
            status=(
                PlatformAccountStatus.CONNECTED
                if credentials
                else PlatformAccountStatus.MOCK
            ),
            is_active=True,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
            last_connected_at=datetime.now(timezone.utc),
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)

        logger.info(
            "platform_account_created platform=%s account_id=%s owner=%s",
            platform, account_id, owner_user_id,
        )
        return account

    async def list_accounts(self, user_ids: Set[int]) -> List[PlatformAccount]:
        stmt = select(PlatformAccount).order_by(PlatformAccount.created_at.desc())
        if user_ids:
            stmt = stmt.where(PlatformAccount.owner_user_id.in_(list(user_ids)))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_account(self, account_id: int, user_ids: Set[int]) -> Optional[PlatformAccount]:
        stmt = select(PlatformAccount).where(PlatformAccount.id == account_id)
        if user_ids:
            stmt = stmt.where(PlatformAccount.owner_user_id.in_(list(user_ids)))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def delete_account(self, account_id: int, owner_user_id: int) -> bool:
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            return False
        await self.session.delete(account)
        await self.session.commit()
        return True

    async def update_account(
        self, account_id: int, owner_user_id: int,
        name: Optional[str] = None,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> PlatformAccount:
        """更新平台账号名称或凭据。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")
        if name is not None:
            account.name = name
        if credentials is not None:
            account.credentials = encrypt_credentials(credentials)
            account.status = (
                PlatformAccountStatus.CONNECTED if credentials
                else PlatformAccountStatus.MOCK
            )
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def toggle_account(self, account_id: int, owner_user_id: int) -> PlatformAccount:
        """切换平台账号启用/停用状态。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")
        account.is_active = not account.is_active
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def search_messages(
        self, account_id: int, owner_user_id: int, keyword: str
    ) -> List[PlatformMessage]:
        """按关键词搜索平台消息。"""
        stmt = (
            select(PlatformMessage)
            .where(
                PlatformMessage.account_id == account_id,
                PlatformMessage.content.ilike(f"%{keyword}%"),
            )
            .order_by(PlatformMessage.created_at.desc())
            .limit(50)
        )
        return list(reversed(list((await self.session.execute(stmt)).scalars().all())))

    async def test_connection(self, account_id: int, owner_user_id: int) -> Dict[str, Any]:
        """测试平台连接状态。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")
        provider = self._get_provider(account)
        try:
            result = await provider.test_connection()
        except Exception as e:  # noqa: BLE001
            result = {"ok": False, "message": str(e)}
        if result.get("ok"):
            account.status = (
                PlatformAccountStatus.MOCK
                if isinstance(provider, MockPlatformProvider)
                else PlatformAccountStatus.CONNECTED
            )
            account.last_connected_at = datetime.now(timezone.utc)
            await self.session.commit()
        elif account.status == PlatformAccountStatus.CONNECTED:
            account.status = PlatformAccountStatus.ERROR
            await self.session.commit()
        return result

    # ==================== 消息收发 ====================

    async def send_message(
        self,
        account_id: int,
        owner_user_id: int,
        to_id: str,
        content: str,
        to_name: Optional[str] = None,
        target_lang: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """发送消息（可选自动翻译）。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")
        if not account.is_active:
            raise ValueError("平台账号已停用")

        send_content = content
        translated = None
        if target_lang:
            tr = await self.translator.translate(content, target_lang)
            send_content = tr["translated"]
            translated = tr

        provider = self._get_provider(account)
        is_mock = isinstance(provider, MockPlatformProvider)

        # 生产环境阻止 Mock 发送
        if is_mock and os.getenv("APP_ENV", "development") == "production":
            raise ValueError("生产环境不允许使用 Mock 平台 Provider 发送消息，请配置真实凭据")

        message = PlatformMessage(
            platform=account.platform,
            account_id=account.id,
            direction=MessageDirection.OUTBOUND,
            from_id=account.account_id,
            from_name=account.name,
            to_id=to_id,
            to_name=to_name,
            content=content,
            translated_content=send_content if translated else None,
            source_lang=(translated or {}).get("source_lang"),
            target_lang=target_lang,
            source_type=EXECUTION_MODE_MOCK if is_mock else EXECUTION_MODE_REAL,
            status=MessageStatus.QUEUED,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        try:
            result = await provider.send_message(to_id, send_content, to_name)
            message.status = MessageStatus(result.get("status", "sent"))
            message.remote_id = result.get("remote_id")
            await self.session.commit()
        except Exception as e:  # noqa: BLE001
            logger.error("platform_send_failed account_id=%s error=%s", account_id, str(e))
            message.status = MessageStatus.FAILED
            await self.session.commit()
            raise ValueError(f"发送失败: {e}")

        # Mock 模式：模拟对方回复，演示"收回复"
        if isinstance(provider, MockPlatformProvider):
            await self._create_mock_reply(account, to_id, to_name, content, owner_user_id, tenant_id)

        return {
            "message_id": message.id,
            "remote_id": message.remote_id,
            "status": message.status.value,
            "translated": send_content if translated else None,
        }

    async def _create_mock_reply(
        self,
        account: PlatformAccount,
        from_id: str,
        from_name: Optional[str],
        last_content: str,
        owner_user_id: int,
        tenant_id: Optional[str],
    ) -> None:
        """创建一条模拟的对方回复（Mock 收消息演示）。"""
        import random

        reply_text = random.choice(_MOCK_REPLIES)
        reply = PlatformMessage(
            platform=account.platform,
            account_id=account.id,
            direction=MessageDirection.INBOUND,
            from_id=from_id,
            from_name=from_name or "对方",
            to_id=account.account_id,
            to_name=account.name,
            content=reply_text,
            source_type=EXECUTION_MODE_MOCK,
            status=MessageStatus.RECEIVED,
            owner_user_id=owner_user_id,
            tenant_id=tenant_id,
            meta={"mock_reply": True, "reply_to": last_content[:50]},
        )
        self.session.add(reply)
        await self.session.commit()

        # 更新/创建联系人
        contact = (
            await self.session.execute(
                select(PlatformContact).where(
                    PlatformContact.account_id == account.id,
                    PlatformContact.remote_id == from_id,
                )
            )
        ).scalar_one_or_none()
        if contact:
            contact.last_message_at = datetime.now(timezone.utc)
        else:
            self.session.add(
                PlatformContact(
                    platform=account.platform,
                    account_id=account.id,
                    remote_id=from_id,
                    name=from_name or "对方",
                    owner_user_id=owner_user_id,
                    tenant_id=tenant_id,
                    last_message_at=datetime.now(timezone.utc),
                )
            )
        await self.session.commit()

    async def receive_messages(self, account_id: int, owner_user_id: int) -> List[PlatformMessage]:
        """拉取平台消息（真实 Provider 通过 Webhook；Mock 读取本地入库消息）。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")

        provider = self._get_provider(account)
        is_mock = isinstance(provider, MockPlatformProvider)
        # 真实 Provider 尝试拉取远端（多数平台以 Webhook 推送，此处留空）
        try:
            remote = await provider.fetch_messages()
        except Exception:  # noqa: BLE001
            remote = []
        for item in remote:
            msg = PlatformMessage(
                platform=account.platform,
                account_id=account.id,
                direction=MessageDirection.INBOUND,
                from_id=item.get("from_id"),
                from_name=item.get("from_name"),
                to_id=account.account_id,
                content=item.get("content", ""),
                source_type=EXECUTION_MODE_MOCK if is_mock else EXECUTION_MODE_REAL,
                status=MessageStatus.RECEIVED,
                owner_user_id=owner_user_id,
            )
            self.session.add(msg)
        if remote:
            await self.session.commit()

        stmt = (
            select(PlatformMessage)
            .where(PlatformMessage.account_id == account.id)
            .order_by(PlatformMessage.created_at.desc())
            .limit(100)
        )
        return list(reversed(list((await self.session.execute(stmt)).scalars().all())))

    async def process_webhook(
        self, account_id: int, body: dict, platform: str = "whatsapp"
    ) -> int:
        """处理平台 Webhook 回调（委托给 WebhookService）。"""
        from src.integrations.webhook import WebhookService

        svc = WebhookService(self.session)
        if platform == "whatsapp":
            return await svc.process_whatsapp(account_id, body)
        if platform == "facebook":
            return await svc.process_facebook(account_id, body)
        if platform == "wechat":
            return await svc.process_wechat(account_id, body)
        return 0

    async def list_messages(self, account_id: int, owner_user_id: int) -> List[PlatformMessage]:
        stmt = (
            select(PlatformMessage)
            .where(PlatformMessage.account_id == account_id)
            .order_by(PlatformMessage.created_at.desc())
            .limit(100)
        )
        return list(reversed(list((await self.session.execute(stmt)).scalars().all())))

    # ==================== 统一收件箱 ====================

    async def get_unified_inbox(
        self,
        user_ids: Set[int],
        platform: Optional[str] = None,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """跨平台统一收件箱消息聚合。"""
        query = select(PlatformMessage)

        # 仅当 user_ids 非空时添加 owner_user_id 过滤
        if user_ids:
            query = query.where(PlatformMessage.owner_user_id.in_(list(user_ids)))

        if platform:
            query = query.where(PlatformMessage.platform == PlatformType(platform))
        if status:
            if status == "unread":
                query = query.where(PlatformMessage.status == MessageStatus.RECEIVED)
            elif status == "outbound":
                query = query.where(PlatformMessage.direction == MessageDirection.OUTBOUND)
            elif status == "inbound":
                query = query.where(PlatformMessage.direction == MessageDirection.INBOUND)
        if keyword:
            query = query.where(PlatformMessage.content.ilike(f"%{keyword}%"))

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 分页
        query = query.order_by(PlatformMessage.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.execute(query)).scalars().all())

        messages = []
        for msg in reversed(rows):
            messages.append({
                "id": msg.id,
                "platform": msg.platform.value,
                "account_id": msg.account_id,
                "direction": msg.direction.value,
                "from_id": msg.from_id,
                "from_name": msg.from_name,
                "to_id": msg.to_id,
                "to_name": msg.to_name,
                "content": msg.content,
                "translated_content": msg.translated_content,
                "source_lang": msg.source_lang,
                "target_lang": msg.target_lang,
                "source_type": msg.source_type,
                "status": msg.status.value,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "remote_id": msg.remote_id,
            })

        return {
            "messages": messages,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_inbox_stats(self, user_ids: Set[int]) -> Dict[str, Any]:
        """收件箱统计信息。"""
        base = select(PlatformMessage)
        if user_ids:
            base = base.where(PlatformMessage.owner_user_id.in_(list(user_ids)))

        # 总消息数
        total = (
            await self.session.execute(
                select(func.count()).select_from(base.subquery())
            )
        ).scalar() or 0

        # 今日消息
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_q = base.where(PlatformMessage.created_at >= today_start)
        today = (
            await self.session.execute(
                select(func.count()).select_from(today_q.subquery())
            )
        ).scalar() or 0

        # 待回复（inbound 且 status=received）
        pending_q = base.where(
            PlatformMessage.direction == MessageDirection.INBOUND,
            PlatformMessage.status == MessageStatus.RECEIVED,
        )
        pending = (
            await self.session.execute(
                select(func.count()).select_from(pending_q.subquery())
            )
        ).scalar() or 0

        # 按平台统计
        platform_q = (
            select(PlatformMessage.platform, func.count())
            .where(PlatformMessage.owner_user_id.in_(list(user_ids)))
            .group_by(PlatformMessage.platform)
        )
        platform_rows = (await self.session.execute(platform_q)).all()
        by_platform = {
            row[0].value if hasattr(row[0], "value") else str(row[0]): row[1]
            for row in platform_rows
        }

        # 回复率
        inbound_total = (
            await self.session.execute(
                select(func.count()).select_from(
                    base.where(
                        PlatformMessage.direction == MessageDirection.INBOUND
                    ).subquery()
                )
            )
        ).scalar() or 0
        replied = 0
        if inbound_total > 0:
            replied = min(pending, inbound_total - pending)
        reply_rate = round((inbound_total - replied) / inbound_total * 100, 1) if inbound_total > 0 else 0

        return {
            "total": total,
            "today": today,
            "pending": pending,
            "reply_rate": reply_rate,
            "by_platform": by_platform,
        }

    async def reply_inbox_message(
        self,
        message_id: int,
        owner_user_id: int,
        content: str,
        target_lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """从统一收件箱回复消息。"""
        # 查找原始消息
        msg = await self.session.execute(
            select(PlatformMessage).where(
                PlatformMessage.id == message_id,
                PlatformMessage.owner_user_id == owner_user_id,
            )
        )
        msg = msg.scalar_one_or_none()
        if not msg:
            raise ValueError("消息不存在")

        # 找到对应的平台账号
        account = await self.session.execute(
            select(PlatformAccount).where(
                PlatformAccount.id == msg.account_id,
                PlatformAccount.owner_user_id == owner_user_id,
            )
        )
        account = account.scalar_one_or_none()
        if not account:
            raise ValueError("平台账号不存在")

        # 确定回复目标
        to_id = msg.from_id if msg.direction == MessageDirection.INBOUND else msg.to_id
        to_name = msg.from_name if msg.direction == MessageDirection.INBOUND else msg.to_name

        return await self.send_message(
            account_id=account.id,
            owner_user_id=owner_user_id,
            to_id=to_id,
            content=content,
            to_name=to_name,
            target_lang=target_lang,
            tenant_id=msg.tenant_id,
        )

    # ==================== 联系人 ====================

    async def list_contacts(self, account_id: int, owner_user_id: int) -> List[PlatformContact]:
        stmt = (
            select(PlatformContact)
            .where(PlatformContact.account_id == account_id)
            .order_by(PlatformContact.updated_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def sync_contacts(self, account_id: int, owner_user_id: int) -> int:
        """从平台拉取联系人（Mock 返回示例联系人）。"""
        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")
        provider = self._get_provider(account)
        remote = await provider.fetch_contacts()
        count = 0
        for item in remote:
            remote_id = item.get("remote_id")
            if not remote_id:
                continue
            contact = (
                await self.session.execute(
                    select(PlatformContact).where(
                        PlatformContact.account_id == account.id,
                        PlatformContact.remote_id == remote_id,
                    )
                )
            ).scalar_one_or_none()
            if not contact:
                self.session.add(
                    PlatformContact(
                        platform=account.platform,
                        account_id=account.id,
                        remote_id=remote_id,
                        name=item.get("name"),
                        phone=item.get("phone"),
                        email=item.get("email"),
                        owner_user_id=owner_user_id,
                    )
                )
                count += 1
        if count:
            await self.session.commit()
        return count

    # ==================== CRM 联动 ====================

    async def sync_contacts_to_crm(
        self, account_id: int, owner_user_id: int
    ) -> Dict[str, int]:
        """将平台联系人同步为 CRM 线索。"""
        from src.crm.service import LeadService

        account = await self.get_account(account_id, {owner_user_id})
        if not account:
            raise ValueError("平台账号不存在")

        # 获取平台联系人
        contacts = await self.list_contacts(account_id, owner_user_id)
        if not contacts:
            # 尝试拉取
            await self.sync_contacts(account_id, owner_user_id)
            contacts = await self.list_contacts(account_id, owner_user_id)

        lead_svc = LeadService(self.session)
        created = 0
        skipped = 0

        for c in contacts:
            # 通过 phone 或 email 判断是否已存在
            if c.phone or c.email:
                existing = await self._find_lead_by_contact(
                    lead_svc, owner_user_id, c.phone, c.email
                )
                if existing:
                    skipped += 1
                    continue

            try:
                await lead_svc.create_lead(
                    data={
                        "name": c.name or c.remote_id,
                        "phone": c.phone or "",
                        "email": c.email or "",
                        "source": "platform",
                        "source_detail": f"{c.platform.value}:{c.remote_id}",
                        "notes": f"来自 {c.platform.value} 平台联系人自动同步",
                    },
                    owner_user_id=owner_user_id,
                    tenant_id=account.tenant_id,
                )
                created += 1
            except Exception as e:  # noqa: BLE001
                logger.error("sync_contact_to_crm_failed contact=%s error=%s", c.id, e)
                skipped += 1

        return {"created": created, "skipped": skipped}

    async def _find_lead_by_contact(
        self,
        lead_svc,
        owner_user_id: int,
        phone: Optional[str],
        email: Optional[str],
    ) -> bool:
        """通过手机号或邮箱查找已存在的线索。"""
        if not phone and not email:
            return False
        from sqlalchemy import or_

        from src.crm.models import Lead

        stmt = select(Lead).where(Lead.owner_user_id == owner_user_id)
        if phone:
            stmt = stmt.where(
                or_(Lead.phone == phone, Lead.whatsapp == phone)
            )
        if email and not phone:
            stmt = stmt.where(Lead.email == email)
        result = (await self.session.execute(stmt)).scalar_one_or_none()
        return result is not None

    async def message_to_lead_activity(
        self, message_id: int, owner_user_id: int
    ) -> Dict[str, Any]:
        """将平台消息转为 CRM 线索活动。"""
        from src.crm.service import LeadService

        msg = await self.session.execute(
            select(PlatformMessage).where(
                PlatformMessage.id == message_id,
                PlatformMessage.owner_user_id == owner_user_id,
            )
        )
        msg = msg.scalar_one_or_none()
        if not msg:
            raise ValueError("消息不存在")

        lead_svc = LeadService(self.session)
        # 通过发送方手机号查找线索
        lead = None
        if msg.from_id:
            from sqlalchemy import or_

            from src.crm.models import Lead

            stmt = select(Lead).where(
                Lead.owner_user_id == owner_user_id,
                or_(Lead.phone == msg.from_id, Lead.whatsapp == msg.from_id),
            )
            lead = (await self.session.execute(stmt)).scalar_one_or_none()

        if not lead:
            # 未找到对应线索，创建新线索
            lead = await lead_svc.create_lead(
                data={
                    "name": msg.from_name or msg.from_id or "未知联系人",
                    "phone": msg.from_id or "",
                    "source": "platform",
                    "source_detail": f"{msg.platform.value}:{msg.from_id}",
                    "notes": f"来自平台消息自动创建: {msg.content[:100]}",
                },
                owner_user_id=owner_user_id,
                tenant_id=msg.tenant_id,
            )

        # 添加活动记录
        activity = await lead_svc.add_activity(
            lead_id=lead.id,
            owner_user_id=owner_user_id,
            activity_type="note",
            content=f"[{msg.platform.value}] {msg.content[:200]}",
            result=f"方向: {msg.direction.value} | 状态: {msg.status.value}",
        )

        return {
            "lead_id": lead.id,
            "lead_name": lead.name,
            "activity_id": activity.id,
            "created": True,
        }
