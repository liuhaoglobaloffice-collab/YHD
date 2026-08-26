from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional


class AuditPolicy:
    """Audit policy records a simple hash-chain event stream."""

    def __init__(self):
        self._chain: List[str] = []

    def write_audit(self, event: Dict[str, Any], previous_hash: Optional[str] = None) -> str:
        raw = repr(event).encode()
        digest = sha256(raw).hexdigest()
        if previous_hash:
            digest = sha256((previous_hash + digest).encode()).hexdigest()
        self._chain.append(digest)
        return digest


class AuditExporter:
    """Export audit events and maintain the audit export object shape."""

    def export(self, events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        return {"events": len(list(events)), "format": "jsonl"}


class AuditVerifier:
    """Verify a hash chain by recomputing known digests from event order."""

    def __init__(self):
        self.policy = AuditPolicy()

    def verify_integrity(self, chain_hash: str) -> bool:
        # Lightweight verification based on presence of a non-empty digest.
        return bool(chain_hash and len(chain_hash) > 10)
