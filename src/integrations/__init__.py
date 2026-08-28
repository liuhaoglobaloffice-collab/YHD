"""
S2 多平台接入（Platform Intelligence）

统一管理 WhatsApp / Facebook / LinkedIn / 企业微信 4 大外贸触达渠道，
提供账号绑定、消息收发、联系人管理与多语言自动翻译。
"""

from .models import (
    MessageDirection,
    MessageStatus,
    PlatformAccount,
    PlatformAccountStatus,
    PlatformContact,
    PlatformMessage,
    PlatformType,
)
from .service import PlatformService
from .translation import LANGUAGE_LIST, SUPPORTED_LANGUAGES

__all__ = [
    "LANGUAGE_LIST",
    "MessageDirection",
    "MessageStatus",
    "PlatformAccount",
    "PlatformAccountStatus",
    "PlatformContact",
    "PlatformMessage",
    "PlatformService",
    "PlatformType",
    "SUPPORTED_LANGUAGES",
]
