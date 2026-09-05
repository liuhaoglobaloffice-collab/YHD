from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class PrincipalType(str, Enum):
    OWNER = "owner"
    USER = "user"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    AGENT = "agent"
    SUB_AGENT = "sub_agent"
    SERVICE = "service"
    EXTERNAL_AGENT = "external_agent"


class IdentityState(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    TERMINATED = "terminated"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True, slots=True)
class Principal:
    principal_id: str
    principal_type: PrincipalType
    owner_id: str | None
    organization_id: str | None
    role: str
    state: IdentityState = IdentityState.ACTIVE
    trust_level: int = 0
    metadata: Mapping[str, str] = field(default_factory=dict)

    def can_execute(self) -> bool:
        return self.state is IdentityState.ACTIVE


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    name: str
    description: str
    risk: RiskLevel
    version: str = "1"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action_id: str
    actor_id: str
    capability_id: str
    action: str
    target: str
    risk: RiskLevel
    organization_id: str | None = None
    tool_id: str | None = None
    resource: str | None = None
    estimated_cost: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    decision: Decision
    reason: str
    policy_id: str | None = None
    approval_scope: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorizationResult:
    request: ActionRequest
    actor: Principal | None
    decision: AuthorizationDecision
    capability: Capability | None
    audit_event_id: str
