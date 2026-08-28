from pathlib import Path


def test_tenant_orm_model_and_route_contract_exist():
    root = Path(__file__).resolve().parents[2]
    models = root / "src" / "database" / "models.py"
    route = root / "src" / "api" / "routes" / "productization.py"

    assert models.exists(), "Missing database model registry"
    assert route.exists(), "Missing productization bridge route"

    model_text = models.read_text(encoding="utf-8")
    route_text = route.read_text(encoding="utf-8")

    assert "class TenantModel(Base):" in model_text
    assert "__tablename__ = \"tenants\"" in model_text
    assert "tenant_id = Column(String(64), unique=True, nullable=False)" in model_text

    assert "create_enterprise(" in route_text
    assert "create_tenant(" in route_text
    assert "session.add(" in route_text
    assert "session.commit()" in route_text
