from __future__ import annotations

from dataclasses import dataclass

from .models import ActionRequest, Capability, Principal, RiskLevel


class CapabilityError(ValueError):
    """Raised when capability registration or assignment is invalid."""


@dataclass(frozen=True, slots=True)
class CapabilityGrant:
    principal_id: str
    capability_id: str
    granted_by: str
    scope: str = "self"


class CapabilityRegistry:
    """Single authority for capability definitions and principal grants."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._grants: dict[tuple[str, str], CapabilityGrant] = {}

    def register(self, capability: Capability) -> Capability:
        if capability.capability_id in self._capabilities:
            raise CapabilityError(f"capability already exists: {capability.capability_id}")
        self._capabilities[capability.capability_id] = capability
        return capability

    def get(self, capability_id: str) -> Capability:
        try:
            return self._capabilities[capability_id]
        except KeyError as exc:
            raise CapabilityError(f"unknown capability: {capability_id}") from exc

    def grant(self, principal: Principal, capability_id: str, granted_by: str, scope: str = "self") -> CapabilityGrant:
        self.get(capability_id)
        if not principal.can_execute():
            raise CapabilityError("cannot grant capabilities to an inactive principal")
        key = (principal.principal_id, capability_id)
        if key in self._grants:
            raise CapabilityError(f"capability already granted: {key}")
        grant = CapabilityGrant(
            principal_id=principal.principal_id,
            capability_id=capability_id,
            granted_by=granted_by,
            scope=scope,
        )
        self._grants[key] = grant
        return grant

    def revoke(self, principal_id: str, capability_id: str) -> None:
        self._grants.pop((principal_id, capability_id), None)

    def is_granted(self, principal_id: str, capability_id: str) -> bool:
        return (principal_id, capability_id) in self._grants

    def authorize_capability(self, request: ActionRequest) -> tuple[bool, Capability | None]:
        capability = self._capabilities.get(request.capability_id)
        if capability is None:
            return False, None
        if not self.is_granted(request.actor_id, request.capability_id):
            return False, capability
        if capability.risk is RiskLevel.CRITICAL and request.risk is not RiskLevel.CRITICAL:
            return False, capability
        return True, capability
