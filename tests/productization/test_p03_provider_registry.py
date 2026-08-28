from pathlib import Path


def test_provider_gateway_registry_contract_exists():
    root = Path(__file__).resolve().parents[2]
    route = root / "src" / "api" / "routes" / "productization.py"
    provider_file = root / "src" / "ai" / "providers.py"

    assert route.exists(), "Missing productization route"
    assert provider_file.exists(), "Missing provider registry implementation"

    route_text = route.read_text(encoding="utf-8")
    provider_text = provider_file.read_text(encoding="utf-8")

    assert "ProviderGateway" in route_text
    assert "ProviderConfig" in route_text
    assert "ProviderType" in route_text
    assert "class ProviderGateway" in provider_text
    assert "class ProviderConfig" in provider_text
