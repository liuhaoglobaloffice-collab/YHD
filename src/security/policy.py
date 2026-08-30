"""
Layer 1: Security & Governance
Policy Engine with Fail Closed principle
"""

from enum import Enum
from typing import Any, Dict, Optional

import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)


class PolicyContext:
    """Context for policy evaluation"""

    def __init__(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.metadata = metadata or {}


class PolicyAction(str, Enum):
    """Policy actions"""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyDecision:
    """Policy evaluation decision"""

    def __init__(
        self,
        action: PolicyAction,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.action = action
        self.reason = reason
        self.metadata = metadata or {}

    def is_allowed(self) -> bool:
        """Check if action is allowed"""
        return self.action == PolicyAction.ALLOW

    def requires_approval(self) -> bool:
        """Check if action requires approval"""
        return self.action == PolicyAction.REQUIRE_APPROVAL


class PolicyEngine:
    """
    Security Policy Engine with Fail Closed principle

    Core Principles:
    1. Default DENY for all unknown policies
    2. Unknown resources = DENY
    3. Policy evaluation failure = DENY
    4. Explicit ALLOW required for access
    """

    def __init__(self):
        self.settings = get_settings()
        self._policies: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_policies()

    def _initialize_default_policies(self) -> None:
        """Initialize default security policies"""

        # Provider Gateway (disabled by default)
        self._policies["provider_gateway"] = {
            "enabled": self.settings.feature_provider_gateway,
            "require_approval": False,
            "allowed_providers": [],  # Empty = none allowed
        }

        # Network Gateway (disabled by default)
        self._policies["network_gateway"] = {
            "enabled": self.settings.feature_network_gateway,
            "require_approval": True,
            "allowed_domains": [],  # Empty = none allowed
        }

        # Browser Gateway (disabled by default)
        self._policies["browser_gateway"] = {
            "enabled": self.settings.feature_browser_gateway,
            "require_approval": True,
            "allowed_domains": [],  # Empty = none allowed
        }

        # External Tools (disabled by default)
        self._policies["external_tools"] = {
            "enabled": self.settings.feature_external_tools,
            "require_approval": True,
            "allowed_tools": [],  # Empty = none allowed
        }

        # Tool execution (enabled by default; security handled by ToolRegistry)
        self._policies["tool"] = {
            "enabled": True,
            "require_approval": False,
        }

        logger.info("policy_engine_initialized", policies=list(self._policies.keys()))

    def evaluate(
        self,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        """
        Evaluate policy for a resource and action

        Args:
            resource: Resource identifier (e.g., "provider_gateway", "network_gateway")
            action: Action to perform (e.g., "call", "access")
            context: Additional context for evaluation

        Returns:
            PolicyDecision with action and reason

        Raises:
            PermissionDeniedError: If policy denies access
        """
        context = context or {}

        logger.info(
            "policy_evaluation",
            resource=resource,
            action=action,
            context=context,
        )

        try:
            # Check if policy exists
            if resource not in self._policies:
                # FAIL CLOSED: Unknown resource = DENY
                logger.warning(
                    "policy_unknown_resource",
                    resource=resource,
                    default_deny=True,
                )
                return PolicyDecision(
                    action=PolicyAction.DENY,
                    reason=f"Unknown resource: {resource} (default DENY)",
                )

            policy = self._policies[resource]

            # Check if feature is enabled
            if not policy.get("enabled", False):
                logger.info(
                    "policy_feature_disabled",
                    resource=resource,
                )
                return PolicyDecision(
                    action=PolicyAction.DENY,
                    reason=f"Feature disabled: {resource}",
                )

            # Check if approval is required
            if policy.get("require_approval", False):
                logger.info(
                    "policy_requires_approval",
                    resource=resource,
                )
                return PolicyDecision(
                    action=PolicyAction.REQUIRE_APPROVAL,
                    reason=f"Approval required for: {resource}",
                )

            # Resource-specific checks
            if resource == "provider_gateway":
                return self._evaluate_provider_gateway(action, context, policy)
            elif resource == "network_gateway":
                return self._evaluate_network_gateway(action, context, policy)
            elif resource == "browser_gateway":
                return self._evaluate_browser_gateway(action, context, policy)
            elif resource == "external_tools":
                return self._evaluate_external_tools(action, context, policy)

            # Default: ALLOW if enabled and no specific rules
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                reason=f"Allowed by default policy: {resource}",
            )

        except Exception as e:
            # FAIL CLOSED: Evaluation error = DENY
            logger.error(
                "policy_evaluation_error",
                resource=resource,
                action=action,
                error=str(e),
            )
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Policy evaluation failed: {str(e)}",
            )

    def _evaluate_provider_gateway(
        self, action: str, context: Dict[str, Any], policy: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate Provider Gateway access"""
        provider = context.get("provider")

        if not provider:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="Provider not specified",
            )

        allowed_providers = policy.get("allowed_providers", [])

        # Empty list = none allowed (Fail Closed)
        if not allowed_providers:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="No providers allowed (whitelist is empty)",
            )

        if provider not in allowed_providers:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Provider not in whitelist: {provider}",
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            reason=f"Provider allowed: {provider}",
        )

    def _evaluate_network_gateway(
        self, action: str, context: Dict[str, Any], policy: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate Network Gateway access"""
        url = context.get("url")

        if not url:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="URL not specified",
            )

        allowed_domains = policy.get("allowed_domains", [])

        # Empty list = none allowed (Fail Closed)
        if not allowed_domains:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="No domains allowed (whitelist is empty)",
            )

        # Check if URL domain is in whitelist
        # (Simplified check - production would use proper URL parsing)
        domain_allowed = any(domain in url for domain in allowed_domains)

        if not domain_allowed:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Domain not in whitelist: {url}",
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            reason=f"Domain allowed: {url}",
        )

    def _evaluate_browser_gateway(
        self, action: str, context: Dict[str, Any], policy: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate Browser Gateway access"""
        url = context.get("url")

        if not url:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="URL not specified",
            )

        allowed_domains = policy.get("allowed_domains", [])

        # Empty list = none allowed (Fail Closed)
        if not allowed_domains:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="No domains allowed (whitelist is empty)",
            )

        domain_allowed = any(domain in url for domain in allowed_domains)

        if not domain_allowed:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Domain not in whitelist: {url}",
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            reason=f"Domain allowed: {url}",
        )

    def _evaluate_external_tools(
        self, action: str, context: Dict[str, Any], policy: Dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate External Tools access"""
        tool_name = context.get("tool_name")

        if not tool_name:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="Tool name not specified",
            )

        allowed_tools = policy.get("allowed_tools", [])

        # Empty list = none allowed (Fail Closed)
        if not allowed_tools:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason="No tools allowed (whitelist is empty)",
            )

        if tool_name not in allowed_tools:
            return PolicyDecision(
                action=PolicyAction.DENY,
                reason=f"Tool not in whitelist: {tool_name}",
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            reason=f"Tool allowed: {tool_name}",
        )

    def update_policy(
        self,
        resource: str,
        policy_data: Dict[str, Any],
    ) -> None:
        """
        Update a policy configuration
        (Only for authorized administrators)
        """
        logger.info("policy_update", resource=resource, policy=policy_data)
        self._policies[resource] = policy_data

    def get_policy(self, resource: str) -> Optional[Dict[str, Any]]:
        """Get policy configuration for a resource"""
        return self._policies.get(resource)


# Global policy engine instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get global policy engine (Singleton)"""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


def reset_policy_engine() -> None:
    """Reset policy engine (for testing only)"""
    global _policy_engine
    _policy_engine = None
