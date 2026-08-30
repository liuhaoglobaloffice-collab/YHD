"""
S2 多平台接入 - Webhook 服务

解析外部平台（WhatsApp / Facebook / 企业微信）的回调消息，
将收到的消息入库并更新联系人信息。
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.models import (
    MessageDirection,
    MessageStatus,
    PlatformAccount,
    PlatformContact,
    PlatformMessage,
    PlatformType,
)

logger = logging.getLogger(__name__)


class WebhookService:
    """Webhook 回调处理服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def process_whatsapp(
        self, account_id: int, body: Dict[str, Any]
    ) -> int:
        """处理 WhatsApp Cloud API 回调。

        WhatsApp 回调格式:
        {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "123456",
                            "id": "wamid.xxx",
                            "text": {"body": "Hello"},
                            "timestamp": "1234567890",
                            "type": "text"
                        }]
                    }
                }]
            }]
        }
        """
        account = await self._get_account(account_id)
        if not account:
            logger.warning("webhook_account_not_found account_id=%s", account_id)
            return 0

        count = 0
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for msg_data in value.get("messages", []):
                    await self._save_inbound_message(
                        account=account,
                        from_id=msg_data.get("from", ""),
                        content=self._extract_whatsapp_content(msg_data),
                        remote_id=msg_data.get("id", ""),
                        msg_type=msg_data.get("type", "text"),
                        from_name=value.get("contacts", [{}])[0].get("profile", {}).get("name"),
                    )
                    count += 1
        if count:
            await self.session.commit()
        return count

    async def process_facebook(
        self, account_id: int, body: Dict[str, Any]
    ) -> int:
        """处理 Facebook Messenger 回调。

        Facebook 回调格式:
        {
            "entry": [{
                "messaging": [{
                    "sender": {"id": "12345"},
                    "message": {"text": "Hello", "mid": "mid.xxx"},
                    "timestamp": 1234567890
                }]
            }]
        }
        """
        account = await self._get_account(account_id)
        if not account:
            logger.warning("webhook_account_not_found account_id=%s", account_id)
            return 0

        count = 0
        for entry in body.get("entry", []):
            for messaging in entry.get("messaging", []):
                message = messaging.get("message", {})
                if not message:
                    continue
                await self._save_inbound_message(
                    account=account,
                    from_id=messaging.get("sender", {}).get("id", ""),
                    content=message.get("text", ""),
                    remote_id=message.get("mid", ""),
                    msg_type="text",
                )
                count += 1
        if count:
            await self.session.commit()
        return count

    async def process_wechat(
        self, account_id: int, body: Dict[str, Any]
    ) -> int:
        """处理企业微信回调。"""
        account = await self._get_account(account_id)
        if not account:
            logger.warning("webhook_account_not_found account_id=%s", account_id)
            return 0

        # 企业微信回调 XML 解析较复杂，此处处理 JSON 格式
        msg_type = body.get("MsgType", body.get("msgtype", ""))
        if msg_type != "text":
            logger.debug("webhook_wechat_skip_non_text type=%s", msg_type)
            return 0

        await self._save_inbound_message(
            account=account,
            from_id=body.get("FromUserName", body.get("fromusername", "")),
            content=body.get("Content", body.get("content", "")),
            remote_id=body.get("MsgId", body.get("msgid", "")),
            msg_type="text",
        )
        await self.session.commit()
        return 1

    def _extract_whatsapp_content(self, msg_data: Dict[str, Any]) -> str:
        """从 WhatsApp 消息数据中提取文本内容。"""
        msg_type = msg_data.get("type", "text")
        if msg_type == "text":
            return msg_data.get("text", {}).get("body", "")
        if msg_type == "button":
            return msg_data.get("button", {}).get("text", "")
        if msg_type == "interactive":
            reply = msg_data.get("interactive", {}).get("button_reply", {})
            return reply.get("title", reply.get("id", ""))
        return ""

    async def _get_account(self, account_id: int) -> Optional[PlatformAccount]:
        stmt = select(PlatformAccount).where(PlatformAccount.id == account_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _save_inbound_message(
        self,
        account: PlatformAccount,
        from_id: str,
        content: str,
        remote_id: str,
        msg_type: str,
        from_name: Optional[str] = None,
    ) -> PlatformMessage:
        """保存收到的消息并更新联系人。"""
        if not content:
            # 跳过非文本消息
            logger.debug("webhook_skip_non_text remote_id=%s", remote_id)
            return None

        # 检查是否已入库（去重）
        if remote_id:
            existing = await self.session.execute(
                select(PlatformMessage).where(PlatformMessage.remote_id == remote_id)
            )
            if existing.scalar_one_or_none():
                return None

        msg = PlatformMessage(
            platform=account.platform,
            account_id=account.id,
            direction=MessageDirection.INBOUND,
            from_id=from_id,
            from_name=from_name or from_id,
            to_id=account.account_id,
            to_name=account.name,
            content=content,
            source_type="REAL",
            status=MessageStatus.RECEIVED,
            remote_id=remote_id,
            owner_user_id=account.owner_user_id,
            tenant_id=account.tenant_id,
            meta={"msg_type": msg_type},
        )
        self.session.add(msg)

        # 更新或创建联系人
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
            if from_name:
                contact.name = from_name
        else:
            self.session.add(
                PlatformContact(
                    platform=account.platform,
                    account_id=account.id,
                    remote_id=from_id,
                    name=from_name or from_id,
                    owner_user_id=account.owner_user_id,
                    tenant_id=account.tenant_id,
                    last_message_at=datetime.now(timezone.utc),
                )
            )

        return msg