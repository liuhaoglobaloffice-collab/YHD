"""
S2 多平台接入 - 数据模型

定义平台账号（PlatformAccount）、平台消息（PlatformMessage）、
平台联系人（PlatformContact）的数据结构。
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)

from src.database.base import Base


class PlatformType(str, Enum):
    """支持的平台类型"""

    WHATSAPP = "whatsapp"  # WhatsApp Business API
    FACEBOOK = "facebook"  # Facebook / Messenger
    LINKEDIN = "linkedin"  # LinkedIn
    WECHAT = "wechat"  # 企业微信


class PlatformAccountStatus(str, Enum):
    """平台账号状态"""

    CONNECTED = "connected"  # 已连接（真实 API）
    MOCK = "mock"  # 开发模式（模拟）
    DISCONNECTED = "disconnected"  # 未连接
    ERROR = "error"  # 连接异常


class MessageDirection(str, Enum):
    """消息方向"""

    OUTBOUND = "outbound"  # 发出
    INBOUND = "inbound"  # 收到


class MessageStatus(str, Enum):
    """消息状态"""

    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    RECEIVED = "received"


class PlatformAccount(Base):
    """平台账号绑定表"""

    __tablename__ = "platform_accounts"

    id = Column(Integer, primary_key=True, index=True, comment="账号ID")

    # 平台信息
    platform = Column(SQLEnum(PlatformType), nullable=False, index=True, comment="平台类型")
    name = Column(String(255), nullable=False, comment="账号名称（备注）")
    account_id = Column(String(255), nullable=False, index=True, comment="平台侧账号ID（如手机号/用户ID）")

    # 凭据（生产环境应加密存储，开发环境可为空走 Mock）
    credentials = Column(JSON, nullable=True, comment="平台凭据（加密存储）")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 状态
    status = Column(
        SQLEnum(PlatformAccountStatus),
        nullable=False,
        default=PlatformAccountStatus.MOCK,
        index=True,
        comment="连接状态",
    )
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )
    last_connected_at = Column(DateTime(timezone=True), nullable=True, comment="最近连接时间")

    __table_args__ = (
        Index("idx_platform_accounts_owner_platform", "owner_user_id", "platform"),
    )

    def __repr__(self) -> str:
        return f"<PlatformAccount(id={self.id}, platform='{self.platform}', name='{self.name}')>"


class PlatformMessage(Base):
    """平台消息表"""

    __tablename__ = "platform_messages"

    id = Column(Integer, primary_key=True, index=True, comment="消息ID")

    # 归属
    platform = Column(SQLEnum(PlatformType), nullable=False, index=True, comment="平台类型")
    account_id = Column(
        Integer, ForeignKey("platform_accounts.id"), nullable=False, index=True, comment="平台账号ID"
    )

    # 消息信息
    direction = Column(
        SQLEnum(MessageDirection), nullable=False, index=True, comment="消息方向"
    )
    remote_id = Column(String(255), nullable=True, comment="平台侧消息ID")
    from_id = Column(String(255), nullable=True, comment="发送方标识")
    from_name = Column(String(255), nullable=True, comment="发送方名称")
    to_id = Column(String(255), nullable=True, comment="接收方标识")
    to_name = Column(String(255), nullable=True, comment="接收方名称")

    # 内容
    content = Column(Text, nullable=False, comment="消息内容")
    translated_content = Column(Text, nullable=True, comment="翻译后的内容")
    source_lang = Column(String(20), nullable=True, comment="源语言")
    target_lang = Column(String(20), nullable=True, comment="目标语言")

    # 执行模式
    source_type = Column(
        String(20), nullable=False, default="MOCK", index=True,
        comment="消息来源类型：REAL / MOCK / NOT_CONFIGURED",
    )

    # 状态
    status = Column(
        SQLEnum(MessageStatus),
        nullable=False,
        default=MessageStatus.QUEUED,
        index=True,
        comment="消息状态",
    )

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="操作人ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 时间戳
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    __table_args__ = (
        Index("idx_platform_messages_account_dir", "account_id", "direction"),
    )

    def __repr__(self) -> str:
        return f"<PlatformMessage(id={self.id}, dir='{self.direction}', status='{self.status}')>"


class PlatformContact(Base):
    """平台联系人表"""

    __tablename__ = "platform_contacts"

    id = Column(Integer, primary_key=True, index=True, comment="联系人ID")

    platform = Column(SQLEnum(PlatformType), nullable=False, index=True, comment="平台类型")
    account_id = Column(
        Integer, ForeignKey("platform_accounts.id"), nullable=False, index=True, comment="平台账号ID"
    )
    remote_id = Column(String(255), nullable=False, comment="平台侧联系人ID")
    name = Column(String(255), nullable=True, comment="联系人名称")
    avatar = Column(String(1000), nullable=True, comment="头像URL")
    phone = Column(String(50), nullable=True, comment="电话/手机号")
    email = Column(String(255), nullable=True, comment="邮箱")
    remark = Column(String(500), nullable=True, comment="备注")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 归属
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="归属用户ID")
    tenant_id = Column(String(64), nullable=True, index=True, comment="租户ID")

    last_message_at = Column(DateTime(timezone=True), nullable=True, comment="最近消息时间")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_platform_contacts_account_remote", "account_id", "remote_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PlatformContact(id={self.id}, name='{self.name}')>"
