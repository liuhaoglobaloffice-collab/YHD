"""
S2 多平台接入 - Provider 实现

包含 4 个真实平台 Provider（WhatsApp/Facebook/LinkedIn/企业微信）
以及开发模式 MockProvider。未配置凭据时由服务层自动回退到 Mock。
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx

from src.integrations.base import PlatformProvider, registry
from src.integrations.models import PlatformAccount, PlatformType

logger = logging.getLogger(__name__)


class MockPlatformProvider(PlatformProvider):
    """开发模式 Provider：模拟收发，便于无凭据联调。"""

    platform = PlatformType.WHATSAPP

    async def test_connection(self) -> Dict[str, Any]:
        return {"ok": True, "message": "开发模式（模拟连接）", "mock": True}

    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        return {
            "remote_id": f"mock-{uuid.uuid4().hex[:12]}",
            "status": "sent",
            "mock": True,
        }

    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return []

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        # 返回一组模拟联系人，方便前端演示
        return [
            {
                "remote_id": "mock-contact-1",
                "name": "Mock 客户 A",
                "phone": "+1 555 100 0001",
            },
            {
                "remote_id": "mock-contact-2",
                "name": "Mock 客户 B",
                "phone": "+1 555 100 0002",
            },
        ]


class WhatsAppProvider(PlatformProvider):
    """WhatsApp Business Cloud API (Graph API)。"""

    platform = PlatformType.WHATSAPP

    @property
    def _base_url(self) -> str:
        return "https://graph.facebook.com/v19.0"

    @property
    def _token(self) -> str:
        return self._credential("access_token") or self._credential("token")

    @property
    def _phone_number_id(self) -> str:
        return self._credential("phone_number_id")

    async def test_connection(self) -> Dict[str, Any]:
        if not (self._token and self._phone_number_id):
            return {"ok": False, "message": "缺少 access_token 或 phone_number_id"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._base_url}/{self._phone_number_id}",
                    headers={"Authorization": f"Bearer {self._token}"},
                )
            return {"ok": resp.status_code == 200, "message": f"HTTP {resp.status_code}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": str(e)}

    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if not (self._token and self._phone_number_id):
            raise RuntimeError("WhatsApp 未配置凭据")
        payload = {
            "messaging_product": "whatsapp",
            "to": to_id,
            "type": "text",
            "text": {"body": content},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self._base_url}/{self._phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return {"remote_id": data.get("messages", [{}])[0].get("id", ""), "status": "sent"}

    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        # 真实场景通过 Webhook 接收，此处返回空
        return []

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        return []


class FacebookProvider(PlatformProvider):
    """Facebook / Messenger Platform API。"""

    platform = PlatformType.FACEBOOK

    @property
    def _page_id(self) -> str:
        return self._credential("page_id")

    @property
    def _token(self) -> str:
        return self._credential("access_token") or self._credential("token")

    async def test_connection(self) -> Dict[str, Any]:
        if not self._token:
            return {"ok": False, "message": "缺少 access_token"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://graph.facebook.com/v19.0/me",
                    params={"access_token": self._token},
                )
            return {"ok": resp.status_code == 200, "message": f"HTTP {resp.status_code}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": str(e)}

    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self._token:
            raise RuntimeError("Facebook 未配置凭据")
        payload = {
            "recipient": {"id": to_id},
            "message": {"text": content},
            "messaging_type": "RESPONSE",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://graph.facebook.com/v19.0/me/messages",
                params={"access_token": self._token},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return {"remote_id": data.get("message_id", ""), "status": "sent"}

    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return []

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        return []


class LinkedInProvider(PlatformProvider):
    """LinkedIn Messaging API。"""

    platform = PlatformType.LINKEDIN

    @property
    def _token(self) -> str:
        return self._credential("access_token") or self._credential("token")

    @property
    def _author_id(self) -> str:
        return self._credential("author_id") or self._credential("person_id")

    async def test_connection(self) -> Dict[str, Any]:
        if not self._token:
            return {"ok": False, "message": "缺少 access_token"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {self._token}"},
                )
            return {"ok": resp.status_code == 200, "message": f"HTTP {resp.status_code}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": str(e)}

    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if not (self._token and self._author_id):
            raise RuntimeError("LinkedIn 未配置凭据")
        payload = {
            "author": f"urn:li:person:{self._author_id}",
            "recipients": [f"urn:li:person:{to_id}"],
            "messageType": "TEXT",
            "content": content,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.linkedin.com/v2/messages",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=payload,
            )
            resp.raise_for_status()
        return {"remote_id": "", "status": "sent"}

    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return []

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        return []


class WeChatWorkProvider(PlatformProvider):
    """企业微信（WeCom）消息接口。"""

    platform = PlatformType.WECHAT

    @property
    def _corp_id(self) -> str:
        return self._credential("corp_id") or self._credential("corpid")

    @property
    def _secret(self) -> str:
        return self._credential("agent_secret") or self._credential("secret")

    @property
    def _agent_id(self) -> str:
        return self._credential("agent_id") or self._credential("agentid")

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": self._corp_id, "corpsecret": self._secret},
            )
            resp.raise_for_status()
            data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"企业微信获取 token 失败: {data.get('errmsg')}")
        return token

    async def test_connection(self) -> Dict[str, Any]:
        if not (self._corp_id and self._secret):
            return {"ok": False, "message": "缺少 corp_id 或 agent_secret"}
        try:
            await self._get_access_token()
            return {"ok": True, "message": "连接成功"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "message": str(e)}

    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        if not (self._corp_id and self._secret):
            raise RuntimeError("企业微信未配置凭据")
        token = await self._get_access_token()
        payload = {
            "touser": to_id,
            "msgtype": "text",
            "agentid": int(self._agent_id) if self._agent_id else 0,
            "text": {"content": content},
            "safe": 0,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://qyapi.weixin.qq.com/cgi-bin/message/send",
                params={"access_token": token},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("errcode") != 0:
            raise RuntimeError(f"企业微信发送失败: {data.get('errmsg')}")
        return {"remote_id": str(data.get("msgid", "")), "status": "sent"}

    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        return []

    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        return []


# 注册到全局平台注册中心
registry.register(PlatformType.WHATSAPP.value, WhatsAppProvider)
registry.register(PlatformType.FACEBOOK.value, FacebookProvider)
registry.register(PlatformType.LINKEDIN.value, LinkedInProvider)
registry.register(PlatformType.WECHAT.value, WeChatWorkProvider)
registry.register("mock", MockPlatformProvider)
