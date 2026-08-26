from src.security.rbac import Role, RBACService, PermissionSet
from src.security.abac import ABACPolicyEngine, PolicyDecision
from src.security.permission import Permission


def test_rbac_role_permission_allows_access():
    service = RBACService()
    service.register_role("admin", {"knowledge.read", "knowledge.write", "task.execute", "workflow.approve", "audit.export"})
    service.assign_role("user-1", "admin")

    allowed = service.check_permission("user-1", "knowledge.write", resource="document")
    assert allowed is True


def test_abac_policy_engine_evaluates_allow_and_deny():
    engine = ABACPolicyEngine()
    allow = engine.evaluate_policy({"user": {"department": "sales"}, "resource": {"owner_department": "sales"}, "environment": {"region": "us"}})
    deny = engine.evaluate_policy({"user": {"department": "sales"}, "resource": {"owner_department": "finance"}, "environment": {"region": "us"}})

    assert allow == PolicyDecision.ALLOW
    assert deny == PolicyDecision.DENY
