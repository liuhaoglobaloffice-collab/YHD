from __future__ import annotations

from .capabilities import CapabilityRegistry
from .events import EventStore, EventType, KernelEvent
from .identity import IdentityService
from .models import (
    ActionRequest,
    AuthorizationDecision,
    AuthorizationResult,
    Decision,
    Principal,
    PrincipalType,
)
from .policy import PolicyEngine, PolicyRule


class KernelService:
    """Unified authority facade for identity, capability, policy and audit."""

    def __init__(self) -> None:
        self.identity = IdentityService()
        self.capabilities = CapabilityRegistry()
        self.policies = PolicyEngine()
        self.events = EventStore()

    def register_principal(
        self,
        *,
        principal_id: str,
        principal_type: PrincipalType,
        owner_id: str | None,
        organization_id: str | None,
        role: str,
        trust_level: int = 0,
    ) -> Principal:
        principal = self.identity.register(
            principal_id=principal_id,
            principal_type=principal_type,
            owner_id=owner_id,
            organization_id=organization_id,
            role=role,
            trust_level=trust_level,
        )
        self.events.append(
            KernelEvent.create(
                EventType.PRINCIPAL_CREATED,
                actor_id=owner_id,
                subject_id=principal_id,
                payload={"principal_type": principal_type.value, "organization_id": organization_id},
            )
        )
        return principal

    def suspend_principal(self, principal_id: str, actor_id: str) -> Principal:
        principal = self.identity.suspend(principal_id)
        self.events.append(
            KernelEvent.create(
                EventType.PRINCIPAL_SUSPENDED,
                actor_id=actor_id,
                subject_id=principal_id,
                payload={"state": principal.state.value},
            )
        )
        return principal

    def revoke_principal(self, principal_id: str, actor_id: str) -> Principal:
        principal = self.identity.revoke(principal_id)
        self.events.append(
            KernelEvent.create(
                EventType.PRINCIPAL_REVOKED,
                actor_id=actor_id,
                subject_id=principal_id,
                payload={"state": principal.state.value},
            )
        )
        return principal

    def terminate_principal(self, principal_id: str, actor_id: str) -> Principal:
        principal = self.identity.terminate(principal_id)
        self.events.append(
            KernelEvent.create(
                EventType.PRINCIPAL_TERMINATED,
                actor_id=actor_id,
                subject_id=principal_id,
                payload={"state": principal.state.value},
            )
        )
        return principal

    def add_policy(self, rule: PolicyRule) -> PolicyRule:
        return self.policies.add_rule(rule)

    def grant_capability(
        self,
        principal_id: str,
        capability_id: str,
        granted_by: str,
        scope: str = "self",
    ):
        grant = self.capabilities.grant(
            self.identity.get(principal_id),
            capability_id,
            granted_by=granted_by,
            scope=scope,
        )
        self.events.append(
            KernelEvent.create(
                EventType.CAPABILITY_GRANTED,
                actor_id=granted_by,
                subject_id=principal_id,
                payload={"capability_id": capability_id, "scope": scope},
            )
        )
        return grant

    def revoke_capability(self, principal_id: str, capability_id: str, revoked_by: str) -> None:
        self.capabilities.revoke(principal_id, capability_id)
        self.events.append(
            KernelEvent.create(
                EventType.CAPABILITY_REVOKED,
                actor_id=revoked_by,
                subject_id=principal_id,
                payload={"capability_id": capability_id},
            )
        )

    def authorize(self, request: ActionRequest) -> AuthorizationResult:
        try:
            actor = self.identity.get(request.actor_id)
        except ValueError:
            actor = None

        if actor is None or not actor.can_execute():
            decision = AuthorizationDecision(
                decision=Decision.DENY,
                reason="inactive or unknown principal",
            )
            return self._audit_result(request, actor, decision, None)

        granted, capability = self.capabilities.authorize_capability(request)
        if not granted:
            decision = AuthorizationDecision(
                decision=Decision.DENY,
                reason="capability missing or incompatible with request risk",
            )
            return self._audit_result(request, actor, decision, capability)

        policy_decision = self.policies.evaluate(request, actor)
        return self._audit_result(request, actor, policy_decision, capability)

    def _audit_result(
        self,
        request: ActionRequest,
        actor: Principal | None,
        decision: AuthorizationDecision,
        capability,
    ) -> AuthorizationResult:
        event = self.events.append(
            KernelEvent.create(
                EventType.POLICY_DECISION,
                actor_id=request.actor_id,
                subject_id=request.action_id,
                payload={
                    "decision": decision.decision.value,
                    "reason": decision.reason,
                    "policy_id": decision.policy_id,
                    "capability_id": request.capability_id,
                    "tool_id": request.tool_id,
                    "target": request.target,
                    "risk": request.risk.value,
                },
            )
        )
        return AuthorizationResult(
            request=request,
            actor=actor,
            decision=decision,
            capability=capability,
            audit_event_id=event.event_id,
        )
