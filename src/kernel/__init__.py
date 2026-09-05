"""LIUHAO X kernel domain primitives.

This package is intentionally dependency-light. It defines the authority boundary
that higher-level runtime components must use rather than implementing parallel
identity/capability/policy models.
"""

from .models import (
    ActionRequest,
    AuthorizationDecision,
    AuthorizationResult,
    Capability,
    Decision,
    IdentityState,
    Principal,
    PrincipalType,
    RiskLevel,
)
from .service import KernelService

__all__ = [
    "ActionRequest",
    "AuthorizationDecision",
    "AuthorizationResult",
    "Capability",
    "Decision",
    "IdentityState",
    "KernelService",
    "Principal",
    "PrincipalType",
    "RiskLevel",
]
