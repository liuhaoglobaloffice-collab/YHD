from pathlib import Path


def test_p03_real_business_flow_bridges_exist_for_productization():
    root = Path(__file__).resolve().parents[2]

    required = [
        root / "src" / "api" / "routes" / "productization.py",
        root / "frontend" / "src" / "services" / "onboarding.ts",
        root / "frontend" / "src" / "pages" / "OnboardingPage.tsx",
    ]

    for path in required:
        assert path.exists(), f"Missing productization flow asset: {path}"

    productization_route = root / "src" / "api" / "routes" / "productization.py"
    route_text = productization_route.read_text(encoding="utf-8")
    for token in [
        "register_user",
        "create_enterprise",
        "create_tenant",
        "configure_provider",
        "create_employee",
        "import_knowledge",
        "run_workflow_demo",
    ]:
        assert token in route_text, f"Missing productization flow token: {token}"

    onboarding_page = root / "frontend" / "src" / "pages" / "OnboardingPage.tsx"
    onboarding_text = onboarding_page.read_text(encoding="utf-8")
    assert "createEnterprise" in onboarding_text
    assert "createTenant" in onboarding_text
    assert "configureProvider" in onboarding_text
    assert "createEmployee" in onboarding_text
    assert "importKnowledge" in onboarding_text
    assert "runWorkflowDemo" in onboarding_text
