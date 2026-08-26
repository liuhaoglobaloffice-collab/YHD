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
    """A tiny in-memory role-based access control registry."""

    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, str] = {}

    def register_role(self, name: str, permissions: Iterable[str]) -> Role:
        role = Role(name=name, permissions=set(permissions))
        self.roles[name] = role
        return role

    def assign_role(self, user_id: str, role_name: str) -> None:
        self.user_roles[user_id] = role_name

    def check_permission(self, user_id: str, permission: str, resource: Optional[str] = None) -> bool:
        role_name = self.user_roles.get(user_id)
        if not role_name:
            return False
        role = self.roles.get(role_name)
        if not role:
            return False
        return permission in role.permissions
