from src.security.audit_policy import AuditPolicy, AuditExporter, AuditVerifier
from src.security.secrets import SecretManager


def test_audit_policy_hash_chain_and_exporter():
    policy = AuditPolicy()
    verifier = AuditVerifier()
    exporter = AuditExporter()

    log_a = {"who": "admin", "action": "task.execute", "resource": "supplier", "result": "success"}
    log_b = {"who": "admin", "action": "task.execute", "resource": "supplier", "result": "success"}

    chain = policy.write_audit(log_a)
    chain = policy.write_audit(log_b, previous_hash=chain)
    exported = exporter.export([log_a, log_b])

    assert verifier.verify_integrity(chain)
    assert exported["events"] >= 2


def test_secret_manager_round_trip_rotation_and_delete():
    manager = SecretManager()
    manager.store_secret("db-password", "super-secret")
    assert manager.get_secret("db-password") == "super-secret"
    rotated = manager.rotate_secret("db-password", "new-secret")
    assert rotated == "new-secret"
    manager.delete_secret("db-password")
    assert manager.get_secret("db-password") is None
