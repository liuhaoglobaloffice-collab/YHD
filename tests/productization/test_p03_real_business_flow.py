from pathlib import Path


def test_p03_real_business_flow_routes_use_existing_repo_integration_contract():
    root = Path(__file__).resolve().parents[2]
    route = root / "src" / "api" / "routes" / "productization.py"
    assert route.exists(), "Missing productization route contract"

    text = route.read_text(encoding="utf-8")

    assert "from src.api.routes.auth import register as auth_register" in text
    assert "from src.api.routes.auth import login as auth_login" in text
    assert "from src.identity.database import get_db_session" in text
    assert "AIEmployeeRegistry" in text
    assert "DocumentMetadata" in text
    assert "TaskService" in text
    assert "AuditService" in text
    assert "provider_registry" in text
