"""
Layer 2: Identity & Access
"""

from src.identity.audit import AuditAction, AuditService
from src.identity.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.identity.database import (
    close_db,
    get_db_session,
    init_db,
)
from src.identity.models import AuditLog, Base, RoleEnum, User
from src.identity.rbac import (
    Permission,
    has_permission,
    is_admin,
    require_admin,
    require_permission,
)

__all__ = [
    # Models
    "User",
    "AuditLog",
    "RoleEnum",
    "Base",
    # Database
    "get_db_session",
    "init_db",
    "close_db",
    # Auth
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    # RBAC
    "Permission",
    "has_permission",
    "require_permission",
    "is_admin",
    "require_admin",
    # Audit
    "AuditService",
    "AuditAction",
]
