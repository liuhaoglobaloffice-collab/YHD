"""Lightweight knowledge security support for Phase 2.4.

Provides the requested interface layer for:
- check_document
- filter_content
- validate_retrieval
- audit_security_event

The implementation stays intentionally small and deterministic, using regex
rules for PII detection and mask replacement in plain text. It remains
compatible with the existing provider and vector-store prototypes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .pii import detect_pii


class KnowledgeSecurityPolicy:
    """Minimal policy object used by the Phase 2.4 RAG security integration."""

    def __init__(self, policy_version: str = "v1.0"):
        self.policy_version = policy_version
        self.audit_log: List[Dict[str, Any]] = []

    def check_document(self, document: Any) -> Dict[str, Any]:
        """Return a lightweight security assessment for a document object."""

        text = ""
        if hasattr(document, "content"):
            text = str(document.content or "")
        elif isinstance(document, dict):
            text = str(document.get("content") or document.get("text") or "")
        elif isinstance(document, str):
            text = document

        pii = detect_pii(text)
        return {
            "document_id": getattr(document, "id", None) or (document.get("id") if isinstance(document, dict) else None),
            "security_status": "passed" if not pii["detected"] else "flagged",
            "pii_detected": pii["detected"],
            "types": pii["types"],
            "matches": pii["matches"],
            "policy_version": self.policy_version,
        }

    def filter_content(self, content: str) -> str:
        """Mask basic PII patterns in the content and return sanitized text."""

        if not content:
            return content

        text = content
        # Email masking
        text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED]", text)
        # Phone masking
        text = re.sub(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", "[REDACTED]", text)
        # Basic identity/address markers
        text = text.replace("SSN", "[REDACTED]")
        text = text.replace("Passport", "[REDACTED]")
        text = text.replace("Tax ID", "[REDACTED]")
        return text

    def validate_retrieval(self, user: Any, documents: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Minimal retrieval validation API.

        Returns a dictionary with `allowed` boolean and `reason` fields.
        Implements a lightweight owner/company-permission style in-memory check.
        """

        if not documents:
            return {"allowed": True, "reason": "no_documents"}

        user_id = None
        company_id = None
        if isinstance(user, dict):
            user_id = user.get("id") or user.get("user_id")
            company_id = user.get("company_id")
        else:
            user_id = getattr(user, "id", None)
            company_id = getattr(user, "company_id", None)

        for doc in documents:
            doc_id = doc.get("document_id") or doc.get("id")
            doc_owner = doc.get("owner_id")
            doc_company = doc.get("company_id")
            access = doc.get("access")
            # If a document has an explicit access restriction, require LHS owner/company.
            # Otherwise allow for local prototype and tests.
            if access == "deny":
                return {"allowed": False, "reason": "document_access_denied", "document_id": doc_id}
            if doc_company and company_id and doc_company != company_id:
                return {"allowed": False, "reason": "company_scope_mismatch", "document_id": doc_id}
            if doc_owner and user_id and doc_owner != user_id:
                return {"allowed": False, "reason": "owner_mismatch", "document_id": doc_id}

        return {"allowed": True, "reason": "allowed", "document_count": len(documents)}

    def audit_security_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Record a security event in memory and return the canonical event payload."""

        record = dict(event)
        record.setdefault("policy_version", self.policy_version)
        record.setdefault("timestamp", "now")
        self.audit_log.append(record)
        return record


def validate_user_access(user: Dict[str, Any], documents: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for a simple user/document access check."""

    policy = KnowledgeSecurityPolicy()
    return policy.validate_retrieval(user, documents)


class KnowledgeSecurityEvent:
    """Lightweight audit event envelope for tests and future integration."""

    def __init__(self, event_type: str = "retrieval", **fields: Any):
        self.event_type = event_type
        self.fields = fields

    def to_dict(self) -> Dict[str, Any]:
        return {"event_type": self.event_type, **self.fields}
