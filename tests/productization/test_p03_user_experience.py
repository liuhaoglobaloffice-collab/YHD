from pathlib import Path


def test_p03_productization_user_experience_assets_exist_and_explicitly_hook_backend_onboarding_route():
    root = Path(__file__).resolve().parents[2]

    required = [
        root / "src" / "api" / "routes" / "productization.py",
        root / "frontend" / "src" / "services" / "onboarding.ts",
        root / "frontend" / "src" / "pages" / "OnboardingPage.tsx",
    ]

    for path in required:
        assert path.exists(), f"Missing P0-3 experience asset: {path}"

    api_router_init = root / "src" / "api" / "routes" / "__init__.py"
    text = api_router_init.read_text(encoding="utf-8")
    assert "productization" in text

    onboarding_page = root / "frontend" / "src" / "pages" / "OnboardingPage.tsx"
    assert "Create Enterprise Space" in onboarding_page.read_text(encoding="utf-8")
    assert "Configure AI Provider" in onboarding_page.read_text(encoding="utf-8")
    assert "Run Workflow Demo" in onboarding_page.read_text(encoding="utf-8")
