"""
Pydantic schemas for API requests and responses
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from src.identity.models import ApprovalStatus, RiskLevel, RoleEnum


# User schemas
class UserBase(BaseModel):
    """Base user schema"""

    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation request"""

    password: str = Field(..., min_length=8, max_length=100)
    role: RoleEnum = RoleEnum.USER


class UserResponse(UserBase):
    """User response"""

    id: int
    role: RoleEnum
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


# Auth schemas
class LoginRequest(BaseModel):
    """Login request"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    token_type: str = "bearer"


# Health check
class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    environment: str
    timestamp: datetime


# System info
class SystemInfoResponse(BaseModel):
    """System information response"""

    version: str
    environment: str
    features: dict
    policies: dict


# Role schemas
class RoleResponse(BaseModel):
    """Role response"""

    id: int
    name: str
    description: Optional[str] = None
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Permission schemas
class PermissionResponse(BaseModel):
    """Permission response"""

    id: int
    resource: str
    action: str
    scope: Optional[str] = None
    description: Optional[str] = None
    code: str

    class Config:
        from_attributes = True


# User management schemas
class UserListResponse(BaseModel):
    """User list response"""

    users: list[UserResponse]
    total: int


class UserStatusUpdate(BaseModel):
    """User status update request"""

    is_active: bool


class UserRoleUpdate(BaseModel):
    """User role update request"""

    role: RoleEnum


# Approval schemas
class ApprovalRequestCreate(BaseModel):
    """Create approval request"""

    request_type: str
    target_resource: str
    target_action: str
    target_id: Optional[str] = None
    payload: Optional[dict] = None
    reason: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    """Approval request response"""

    id: int
    request_type: str
    requester_id: int
    target_resource: str
    target_action: str
    target_id: Optional[str] = None
    risk_level: RiskLevel
    status: ApprovalStatus
    reason: Optional[str] = None
    approver_id: Optional[int] = None
    review_reason: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    """Approval decision (approve/reject)"""

    reason: Optional[str] = None


class ApprovalListResponse(BaseModel):
    """Approval list response"""

    requests: list[ApprovalRequestResponse]
    total: int


# Audit schemas
class AuditLogResponse(BaseModel):
    """Audit log response"""

    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    status: str
    error_message: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Audit log list response"""

    logs: list[AuditLogResponse]
    total: int
