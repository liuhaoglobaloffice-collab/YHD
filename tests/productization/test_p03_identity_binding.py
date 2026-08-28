from pathlib import Path


def test_p03_identity_binding_contract_is_missing_in_repo():
    root = Path(__file__).resolve().parents[2]
    models = root / "src" / "database" / "models.py"
    identity_models = root / "src" / "identity" / "models.py"
    route = root / "src" / "api" / "routes" / "productization.py"

    model_text = models.read_text(encoding="utf-8")
    identity_text = identity_models.read_text(encoding="utf-8")
    route_text = route.read_text(encoding="utf-8")

    assert "class EnterpriseModel(Base):" in model_text
    assert "enterprise_id = Column(String(36), ForeignKey(\"enterprises.id\"), nullable=False)" in model_text
    assert "owner_id = Column(Integer, ForeignKey(\"users.id\"), nullable=False)" in model_text
    assert "tenant_id" in identity_text

    assert "create_enterprise(" in route_text
    assert "create_tenant(" in route_text
    assert "enterprise_id" in route_text
    assert "tenant_id" in route_text
    assert "owner_id" in route_text
