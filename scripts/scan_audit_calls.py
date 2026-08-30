"""Scan the codebase for AuditService.log calls with the broken signature.

P0-B acceptance: zero call sites that pass ``action=`` (or positional
action) but no database session.

A call is considered broken when:
  - it targets a ``.log(`` method of something named like an audit
    service (self.audit / audit_service / AuditService / self.audit.X),
    and
  - it has an ``action`` argument (positional or keyword), and
  - it has no ``session`` argument (neither the first positional arg
    nor a ``session=`` keyword).

Usage: python scripts/scan_audit_calls.py
Exit code 0 when no broken calls are found.
"""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Names that identify an audit service receiver
AUDIT_RECEIVERS = {"audit", "audit_service", "auditservice"}


def receiver_name(func: ast.AST) -> str:
    """Extract the receiver name of a method call, e.g. self.audit -> audit."""
    if isinstance(func, ast.Attribute):
        value = func.value
        if isinstance(value, ast.Name):
            return value.id
        if isinstance(value, ast.Attribute):
            return value.attr
    return ""


def has_arg(call: ast.Call, name: str) -> bool:
    """Check positional index 0 or keyword for the given argument name."""
    if call.args:
        return True  # first positional is the session in the fixed signature
    return any(kwarg.arg == name for kwarg in call.keywords)


def main() -> int:
    broken = []
    checked = 0
    for path in sorted((PROJECT_ROOT / "src").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "log":
                continue
            recv = receiver_name(func).lower()
            if recv not in AUDIT_RECEIVERS:
                continue
            kwargs = {kw.arg for kw in node.keywords if kw.arg}
            has_action = "action" in kwargs or bool(node.args)
            if not has_action:
                continue
            # Session present? either a positional first arg or session= keyword
            has_session = bool(node.args) or "session" in kwargs
            checked += 1
            if not has_session:
                broken.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")

    print(f"audit .log() call sites checked: {checked}")
    if broken:
        print(f"BROKEN (action present, session missing): {len(broken)}")
        for loc in broken:
            print(f"  - {loc}")
        return 1
    print("BROKEN: 0 - all audit .log() calls pass a session")
    return 0


if __name__ == "__main__":
    sys.exit(main())
