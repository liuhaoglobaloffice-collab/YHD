from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Dict, Optional


@dataclass
class Tenant:
    tenant_id: str
    tenant_name: str
    status: str = "ACTIVE"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)


class TenantContext:
    """Thread-local style context object for the active tenant."""

    def __init__(self):
        self._current: Optional[Tenant] = None

    def current_tenant(self) -> Optional[Tenant]:
        return self._current

    def switch_tenant(self, tenant: Tenant) -> Tenant:
        self._current = tenant
        return tenant


class TenantValidator:
    """Lightweight cross-tenant validator as requested in Phase 5."""

    def validate_tenant_access(self, tenant_a: str, tenant_b: str) -> bool:
        return tenant_a == tenant_b
