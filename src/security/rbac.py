"""DEPRECATED — P0-3 统一 RBAC。

此模块保留作为兼容 shim，实际业务与测试的活跃实现为 `src.identity.rbac`。
直接导入本模块会抛出 DeprecationWarning；暴露的 Role / PermissionSet / RBACService
仍保持与旧 test_rbac_abac.py 一致的轻量内存 API，不会破坏现有调用方。
"""
from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "src.security.rbac 已废弃，请迁移到 src.identity.rbac。"
    " security.rbac 仅保留最小兼容 shim。",
    DeprecationWarning,
    stacklevel=2,
)

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set


@dataclass
class Role:
    name: str
    permissions: Set[str] = field(default_factory=set)


class PermissionSet:
    """Alias class used by tests to check permission registration."""

    def __init__(self, permissions: Optional[Iterable[str]] = None):
        self.permissions = set(permissions or [])


class RBACService:
    """Legacy compatibility shim — 仅用于通过最小 RBAC 契约。

    实际业务请使用 `src.identity.rbac.RBACService`。
    """

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, str] = {}

    def register_role(self, name: str, permissions: Iterable[str]) -> Role:
        role = Role(name=name, permissions=set(permissions))
        self.roles[name] = role
        return role

    def assign_role(self, user_id: str, role_name: str) -> None:
        self.user_roles[str(user_id)] = role_name

    def check_permission(self, user_id: str, permission: str, resource: Optional[str] = None) -> bool:
        role_name = self.user_roles.get(str(user_id))
        if not role_name:
            return False
        role = self.roles.get(role_name)
        if not role:
            return False
        return permission in role.permissions


__all__ = ["Role", "PermissionSet", "RBACService"]
