from pathlib import Path


def test_ai_employee_registry_contract_exists():
    root = Path(__file__).resolve().parents[2]
    route = root / "src" / "api" / "routes" / "productization.py"
    registry = root / "src" / "workforce" / "registry.py"
    model = root / "src" / "workforce" / "models.py"

    assert route.exists(), "Missing productization route"
    assert registry.exists(), "Missing workforce registry implementation"
    assert model.exists(), "Missing workforce data model"

    route_text = route.read_text(encoding="utf-8")
    registry_text = registry.read_text(encoding="utf-8")
    model_text = model.read_text(encoding="utf-8")

    assert "AIEmployeeRegistry" in route_text
    assert "register(" in registry_text
    assert "class AIEmployee" in model_text
    assert "owner_id" in model_text
