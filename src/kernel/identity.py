from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import IdentityState, Principal, PrincipalType


class IdentityError(ValueError):
    """Raised for invalid identity lifecycle or ownership relationships."""


class IdentityService:
    """In-process identity authority used by the kernel.

    Persistence belongs to the next storage phase. Even at this layer, callers
    get one authoritative principal registry and cannot execute without an active
    principal.
    """

    def __init__(self) -> None:
        self._principals: dict[str, Principal] = {}

    def register(
        self,
        *,
        principal_id: str,
        principal_type: PrincipalType,
        owner_id: str | None,
        organization_id: str | None,
        role: str,
        trust_level: int = 0,
    ) -> Principal:
        if principal_id in self._principals:
            raise IdentityError(f"principal already exists: {principal_id}")
        if principal_type in {PrincipalType.AGENT, PrincipalType.SUB_AGENT} and not owner_id:
            raise IdentityError("agents and sub-agents require an owner_id")
        if not 0 <= trust_level <= 100:
            raise IdentityError("trust_level must be between 0 and 100")
        principal = Principal(
            principal_id=principal_id,
            principal_type=principal_type,
            owner_id=owner_id,
            organization_id=organization_id,
            role=role,
            trust_level=trust_level,
        )
        self._principals[principal_id] = principal
        return principal

    def get(self, principal_id: str) -> Principal:
        try:
            return self._principals[principal_id]
        except KeyError as exc:
            raise IdentityError(f"unknown principal: {principal_id}") from exc

    def all(self) -> Iterable[Principal]:
        return tuple(self._principals.values())

    def suspend(self, principal_id: str) -> Principal:
        return self._set_state(principal_id, IdentityState.SUSPENDED)

    def revoke(self, principal_id: str) -> Principal:
        return self._set_state(principal_id, IdentityState.REVOKED)

    def terminate(self, principal_id: str) -> Principal:
        return self._set_state(principal_id, IdentityState.TERMINATED)

    def activate(self, principal_id: str) -> Principal:
        principal = self.get(principal_id)
        if principal.state in {IdentityState.REVOKED, IdentityState.TERMINATED}:
            raise IdentityError("revoked or terminated principals cannot be reactivated")
        return self._set_state(principal_id, IdentityState.ACTIVE)

    def _set_state(self, principal_id: str, state: IdentityState) -> Principal:
        updated = replace(self.get(principal_id), state=state)
        self._principals[principal_id] = updated
        return updated
