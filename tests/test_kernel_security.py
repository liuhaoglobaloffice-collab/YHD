from src.kernel.capabilities import CapabilityError
from src.kernel.models import (
    ActionRequest,
    Capability,
    Decision,
    PrincipalType,
    RiskLevel,
)
from src.kernel.policy import PolicyRule
from src.kernel.service import KernelService


def make_kernel() -> KernelService:
    kernel = KernelService()
    kernel.register_principal(
        principal_id="owner-1",
        principal_type=PrincipalType.OWNER,
        owner_id=None,
        organization_id="org-1",
        role="owner",
    )
    kernel.register_principal(
        principal_id="agent-1",
        principal_type=PrincipalType.AGENT,
        owner_id="owner-1",
        organization_id="org-1",
        role="researcher",
    )
    kernel.capabilities.register(
        Capability(
            capability_id="browser.read",
            name="Browser Read",
            description="Read permitted web resources.",
            risk=RiskLevel.LOW,
        )
    )
    kernel.capabilities.grant(
        kernel.identity.get("agent-1"),
        "browser.read",
        granted_by="owner-1",
    )
    return kernel


def request(**overrides):
    values = {
        "action_id": "action-1",
        "actor_id": "agent-1",
        "capability_id": "browser.read",
        "action": "browser.read",
        "target": "https://example.com",
        "risk": RiskLevel.LOW,
        "organization_id": "org-1",
    }
    values.update(overrides)
    return ActionRequest(**values)


def test_default_deny_when_no_policy_matches() -> None:
    result = make_kernel().authorize(request())
    assert result.decision.decision is Decision.DENY
    assert result.audit_event_id


def test_allow_requires_identity_capability_and_policy() -> None:
    kernel = make_kernel()
    kernel.add_policy(
        PolicyRule(
            policy_id="read-allow",
            effect=Decision.ALLOW,
            actions=frozenset({"browser.read"}),
            capabilities=frozenset({"browser.read"}),
            roles=frozenset({"researcher"}),
            risk_levels=frozenset({RiskLevel.LOW}),
            organizations=frozenset({"org-1"}),
            reason="approved read access",
        )
    )
    result = kernel.authorize(request())
    assert result.decision.decision is Decision.ALLOW
    assert result.capability is not None


def test_suspended_agent_cannot_execute_even_with_policy() -> None:
    kernel = make_kernel()
    kernel.add_policy(
        PolicyRule(
            policy_id="allow",
            effect=Decision.ALLOW,
            actions=frozenset({"browser.read"}),
        )
    )
    kernel.identity.suspend("agent-1")
    result = kernel.authorize(request())
    assert result.decision.decision is Decision.DENY
    assert "inactive" in result.decision.reason


def test_missing_capability_is_denied() -> None:
    kernel = make_kernel()
    kernel.add_policy(
        PolicyRule(policy_id="allow", effect=Decision.ALLOW, actions=frozenset({"db.write"}))
    )
    result = kernel.authorize(
        request(capability_id="database.write", action="db.write")
    )
    assert result.decision.decision is Decision.DENY
    assert result.capability is None


def test_agent_requires_owner_identity() -> None:
    kernel = KernelService()
    try:
        kernel.register_principal(
            principal_id="agent-no-owner",
            principal_type=PrincipalType.AGENT,
            owner_id=None,
            organization_id="org-1",
            role="worker",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("agent without owner must be rejected")
