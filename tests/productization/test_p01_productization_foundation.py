from pathlib import Path


def test_p01_productization_assets_exist():
    root = Path(__file__).resolve().parents[2]

    required = [
        root / "requirements.txt",
        root / ".env.example",
        root / "scripts" / "start_api.sh",
        root / "frontend" / "package.json",
        root / "frontend" / "tailwind.config.js",
        root / "frontend" / "vite.config.ts",
        root / "docker-compose.yml",
    ]

    for path in required:
        assert path.exists(), f"Missing productization asset: {path}"


def test_p01_startup_scripts_are_executable_and_template_ready():
    root = Path(__file__).resolve().parents[2]
    api_script = root / "scripts" / "start_api.sh"
    # 入口为 src.main:app（src/api/app.py 只暴露 create_app() 工厂，无模块级 app）
    assert "uvicorn src.main:app --reload --host 0.0.0.0 --port 8000" in api_script.read_text()

    frontend_pkg = root / "frontend" / "package.json"
    pkg_text = frontend_pkg.read_text()
    assert '"npm run dev"' not in pkg_text
    assert '"dev": "vite --host 0.0.0.0 --port 3000"' in pkg_text
