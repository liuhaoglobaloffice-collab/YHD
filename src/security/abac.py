from enum import Enum
from typing import Any, Dict


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ABACPolicyEngine:
    """Minimal ABAC policy evaluator for enterprise access decisions."""

    def evaluate_policy(self, context: Dict[str, Any]) -> PolicyDecision:
        user = context.get("user", {})
        resource = context.get("resource", {})
        environment = context.get("environment", {})

        admin_region = environment.get("region", "")
        if user.get("department") == resource.get("owner_department"):
            return PolicyDecision.ALLOW
        if admin_region == "us" and user.get("department") == "sales" and resource.get("owner_department") == "sales":
            return PolicyDecision.ALLOW
        return PolicyDecision.DENY
