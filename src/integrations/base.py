"""
S2 多平台接入 - Provider 抽象与注册中心

统一平台 Provider 接口：测试连接、发送消息、拉取消息、拉取联系人。
任何平台接入（WhatsApp/Facebook/LinkedIn/企业微信）都实现该接口。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.integrations.models import PlatformAccount, PlatformType

logger = logging.getLogger(__name__)


class PlatformProvider(ABC):
    """平台 Provider 基类"""

    platform: PlatformType

    def __init__(self, account: PlatformAccount, credentials: Optional[Dict[str, Any]] = None):
        self.account = account
        self.credentials = credentials or (account.credentials or {})

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """测试与平台的连接。返回 {"ok": bool, "message": str}"""

    @abstractmethod
    async def send_message(
        self, to_id: str, content: str, to_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送消息。返回 {"remote_id": str, "status": str}"""

    @abstractmethod
    async def fetch_messages(
        self, since: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """拉取收件箱消息。返回消息字典列表"""

    @abstractmethod
    async def fetch_contacts(self) -> List[Dict[str, Any]]:
        """拉取联系人。返回联系人字典列表"""

    def _credential(self, key: str, default: str = "") -> str:
        """安全读取凭据。"""
        return str(self.credentials.get(key) or default)


class PlatformRegistry:
    """平台 Provider 注册中心"""

    def __init__(self):
        self._providers: Dict[str, type] = {}

    def register(self, platform_type: str, provider_cls: type) -> None:
        """注册平台 Provider 类。"""
        self._providers[platform_type] = provider_cls
        logger.info("platform_provider_registered platform=%s", platform_type)

    def get_provider_class(self, platform_type: str) -> Optional[type]:
        """获取平台 Provider 类。"""
        return self._providers.get(platform_type)

    def list_platforms(self) -> List[str]:
        """列出已注册平台。"""
        return list(self._providers.keys())


# 全局平台注册中心
registry = PlatformRegistry()
