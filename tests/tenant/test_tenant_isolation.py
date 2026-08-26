from src.security.tenant import Tenant, TenantContext, TenantValidator


def test_tenant_a_cannot_access_tenant_b_data():
    context = TenantContext()
    tenant_a = Tenant(tenant_id="tenant-a", tenant_name="Acme", status="ACTIVE")
    tenant_b = Tenant(tenant_id="tenant-b", tenant_name="Beta", status="ACTIVE")

    context.switch_tenant(tenant_a)
    assert context.current_tenant().tenant_id == "tenant-a"

    validator = TenantValidator()
    assert validator.validate_tenant_access("tenant-a", "tenant-b") is False
    assert validator.validate_tenant_access("tenant-a", "tenant-a") is True
