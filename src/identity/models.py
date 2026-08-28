"""
Database models for Identity, RBAC, and Audit
"""

import enum
from datetime import UTC, datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import unified Base from database layer to ensure all models share the same metadata
from src.database.base import Base


class BusinessRole(str, enum.Enum):
    """预定义业务角色（外贸企业团队分工）"""

    SALES = "sales"           # 销售 - 客户开发、CRM跟进、WhatsApp/Facebook营销
    PURCHASING = "purchasing" # 采购 - 供应商搜索、分析、采购谈判
    OPERATIONS = "operations" # 运营 - 数据运营、SEO、内容发布、社媒运营
    AI_ADMIN = "ai_admin"     # AI管理员 - 管理AI员工、技能、模型配置
    GENERAL = "general"       # 通用 - 多功能综合岗

class RoleEnum(str, enum.Enum):
    """System roles (RBAC base level)"""

    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class AccountType(str, enum.Enum):
    """Account type for main/sub account hierarchy (S1)."""

    OWNER = "owner"  # 主账号（老板）- 可指挥鎏灏
    SUB = "sub"  # 子账号（受限，只读/协作）


class ApprovalStatus(str, enum.Enum):
    """Approval request status"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RiskLevel(str, enum.Enum):
    """Risk level for approval requests"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Association table for Role-Permission many-to-many
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class User(Base):
    """User identity"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Productization tenant binding
    tenant_id: Mapped[Optional[str]] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)

    # Role
    role: Mapped[RoleEnum] = mapped_column(SQLEnum(RoleEnum), default=RoleEnum.USER, nullable=False)

    # 业务角色（子账号按外贸分工分类）
    business_role: Mapped[Optional[BusinessRole]] = mapped_column(
        SQLEnum(BusinessRole), nullable=True
    )

    # S1: 主/子账号体系
    account_type: Mapped[AccountType] = mapped_column(
        SQLEnum(AccountType), default=AccountType.OWNER, nullable=False
    )
    parent_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    # V4: 子账号月度 AI 预算（USD/月，NULL=不限）
    ai_budget_monthly: Mapped[Optional[float]] = mapped_column(nullable=True)

    # 数据权限范围
    # all = 全公司数据，department = 本部门，self = 仅本人数据
    class DataScope(str, enum.Enum):
        ALL = "all"
        DEPARTMENT = "department"
        SELF = "self"

    data_scope: Mapped[str] = mapped_column(
        String(20), default=DataScope.SELF.value, nullable=False
    )

    # 权限配置（细粒度权限开关，JSON存储）
    # 格式: {"customer:read": true, "whatsapp:send": false, ...}
    permissions_config: Mapped[Optional[dict]] = mapped_column(JSON)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 子账号自助注册审批状态: pending / approved / rejected；None 视为已通过（存量/主账号直接创建）
    approval_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        foreign_keys="[ApprovalRequest.requester_id]",
        back_populates="requester",
        cascade="all, delete-orphan",
    )
    approved_requests: Mapped[list["ApprovalRequest"]] = relationship(
        "ApprovalRequest",
        foreign_keys="[ApprovalRequest.approver_id]",
        back_populates="approver",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class AuditLog(Base):
    """Audit log for all critical operations"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Who
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    # What
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSON)

    # Result
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # success/failure/denied
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

    # When
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"


class Role(Base):
    """Role model for flexible RBAC (Stage 2)"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """Permission model for flexible RBAC (Stage 2)"""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scope: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self) -> str:
        scope_str = f":{self.scope}" if self.scope else ""
        return f"<Permission({self.resource}:{self.action}{scope_str})>"

    @property
    def code(self) -> str:
        """Full permission code like 'users:read' or 'users:read:own'"""
        if self.scope:
            return f"{self.resource}:{self.action}:{self.scope}"
        return f"{self.resource}:{self.action}"


class Session(Base):
    """User session tracking (Stage 2)"""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, active={self.is_active})>"


class ApprovalRequest(Base):
    """Approval request for high-risk operations (Stage 2)"""

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    target_resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_action: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(255))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)
    risk_level: Mapped[RiskLevel] = mapped_column(SQLEnum(RiskLevel), nullable=False, index=True)
    status: Mapped[ApprovalStatus] = mapped_column(
        SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False, index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    review_reason: Mapped[Optional[str]] = mapped_column(Text)
    audit_log_id: Mapped[Optional[int]] = mapped_column(ForeignKey("audit_logs.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    requester: Mapped["User"] = relationship(
        "User", foreign_keys=[requester_id], back_populates="approval_requests"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approver_id], back_populates="approved_requests"
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest(id={self.id}, type={self.request_type}, status={self.status}, risk={self.risk_level})>"
