from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4


class EventType(str, Enum):
    PRINCIPAL_CREATED = "PrincipalCreated"
    PRINCIPAL_SUSPENDED = "PrincipalSuspended"
    PRINCIPAL_REVOKED = "PrincipalRevoked"
    PRINCIPAL_TERMINATED = "PrincipalTerminated"
    CAPABILITY_GRANTED = "CapabilityGranted"
    CAPABILITY_REVOKED = "CapabilityRevoked"
    POLICY_DECISION = "PolicyDecision"


@dataclass(frozen=True, slots=True)
class KernelEvent:
    event_id: str
    event_type: EventType
    actor_id: str | None
    subject_id: str | None
    payload: Mapping[str, Any]
    timestamp: str

    @classmethod
    def create(
        cls,
        event_type: EventType,
        *,
        actor_id: str | None,
        subject_id: str | None,
        payload: Mapping[str, Any],
    ) -> "KernelEvent":
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            actor_id=actor_id,
            subject_id=subject_id,
            payload=dict(payload),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


class EventStore:
    """Append-only event sink for the kernel foundation.

    This in-process store is the reference behavior. A durable event store is a
    later infrastructure concern, but higher layers must depend on this contract.
    """

    def __init__(self) -> None:
        self._events: list[KernelEvent] = []

    def append(self, event: KernelEvent) -> KernelEvent:
        self._events.append(event)
        return event

    def list(self) -> tuple[KernelEvent, ...]:
        return tuple(self._events)
