from pathlib import Path
import json


def test_p02_frontend_react_structure_and_router_contract_exist():
    root = Path(__file__).resolve().parents[2]
    pkg = root / "frontend" / "package.json"
    assert pkg.exists(), "frontend package manifest must exist"

    manifest = json.loads(pkg.read_text(encoding="utf-8"))
    assert manifest["type"] == "module"
    assert manifest["scripts"]["dev"].startswith("vite")
    assert manifest["dependencies"].get("react")
    assert manifest["dependencies"].get("react-router-dom")

    src_dir = root / "frontend" / "src"
    pages_dir = src_dir / "pages"
    components_dir = src_dir / "components"
    routes_dir = src_dir / "routes"
    services_dir = src_dir / "services"
    hooks_dir = src_dir / "hooks"
    utils_dir = src_dir / "utils"

    assert src_dir.exists(), "frontend/src must exist"
    assert pages_dir.exists(), "frontend/src/pages must exist"
    assert components_dir.exists(), "frontend/src/components must exist"
    assert routes_dir.exists(), "frontend/src/routes must exist"
    assert services_dir.exists(), "frontend/src/services must exist"
    assert hooks_dir.exists(), "frontend/src/hooks must exist"
    assert utils_dir.exists(), "frontend/src/utils must exist"

    routes_index = routes_dir / "index.tsx"
    assert routes_index.exists(), "React Router route index must exist"

    required_pages = [
        "DashboardPage.tsx",
        "EmployeesPage.tsx",
        "WorkflowPage.tsx",
        "SecurityPage.tsx",
        "ModelsPage.tsx",
        "MetricsPage.tsx",
        "OnboardingPage.tsx",
    ]

    for filename in required_pages:
        assert (pages_dir / filename).exists(), f"Missing page contract: {filename}"

    assert (components_dir / "Layout.tsx").exists(), "Missing Layout component"
    assert (components_dir / "Sidebar.tsx").exists(), "Missing Sidebar component"
    assert (components_dir / "Header.tsx").exists(), "Missing Header component"

    assert (services_dir / "api.ts").exists(), "Missing API service base layer"
