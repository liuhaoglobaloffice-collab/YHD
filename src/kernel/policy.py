from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from .models import ActionRequest, AuthorizationDecision, Decision, Principal, RiskLevel


@dataclass(frozen=True, slots=True)
class PolicyRule:
    policy_id: str
    effect: Decision
    actions: frozenset[str] = field(default_factory=frozenset)
    capabilities: frozenset[str] = field(default_factory=frozenset)
    roles: frozenset[str] = field(default_factory=frozenset)
    risk_levels: frozenset[RiskLevel] = field(default_factory=frozenset)
    organizations: frozenset[str] = field(default_factory=frozenset)
    reason: str = ""
    approval_scope: str | None = None

    def matches(self, request: ActionRequest, actor: Principal) -> bool:
        return (
            (not self.actions or request.action in self.actions)
            and (not self.capabilities or request.capability_id in self.capabilities)
            and (not self.roles or actor.role in self.roles)
            and (not self.risk_levels or request.risk in self.risk_levels)
            and (not self.organizations or request.organization_id in self.organizations)
        )


class PolicyEngine:
    """Deterministic first-match policy evaluator.

    The default-deny posture is intentional: no matching rule means DENY.
    """

    def __init__(self, rules: Iterable[PolicyRule] = ()) -> None:
        self._rules: list[PolicyRule] = list(rules)

    def add_rule(self, rule: PolicyRule) -> PolicyRule:
        if any(existing.policy_id == rule.policy_id for existing in self._rules):
            raise ValueError(f"policy already exists: {rule.policy_id}")
        self._rules.append(rule)
        return rule

    def evaluate(self, request: ActionRequest, actor: Principal) -> AuthorizationDecision:
        for rule in self._rules:
            if rule.matches(request, actor):
                return AuthorizationDecision(
                    decision=rule.effect,
                    reason=rule.reason or f"matched policy {rule.policy_id}",
                    policy_id=rule.policy_id,
                    approval_scope=rule.approval_scope,
                )
        return AuthorizationDecision(
            decision=Decision.DENY,
            reason="no matching policy; default deny",
        )
