"""Rule-based PII detection helpers for Phase 2.4.

Designed to stay lightweight and dependency-free, and to integrate with the
existing knowledge package without introducing a security framework.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})")
IDENTITY_RE = re.compile(r"\b(?:SSN|Tax ID|Passport|Government ID)\b", flags=re.I)
ADDRESS_RE = re.compile(r"\b(?:Street|Street Address|Avenue|Road|Apartment|Suite|City|State|ZIP)\b", flags=re.I)


def detect_pii(text: str) -> Dict[str, Any]:
    """Return a light rule-based PII assessment.

    Returns the required PII response shape:
    {
        "detected": bool,
        "types": [..],
        "matches": [..],
    }
    """

    detected = False
    types: List[str] = []
    matches: List[str] = []

    email_hits = EMAIL_RE.findall(text or "")
    if email_hits:
        detected = True
        types.append("email")
        matches.extend(email_hits)

    phone_hits = PHONE_RE.findall(text or "")
    if phone_hits:
        detected = True
        types.append("phone")
        matches.extend(phone_hits)

    if IDENTITY_RE.search(text or ""):
        detected = True
        types.append("identity")
        matches.append("identity-marker")

    if ADDRESS_RE.search(text or ""):
        detected = True
        types.append("address")
        matches.append("address-marker")

    return {
        "detected": detected,
        "types": sorted(set(types)),
        "matches": matches,
    }
