from pathlib import Path

from src.ui.governance import GovernanceCenter


def test_phase8_governance_document_assets_exist():
    repo_root = Path(__file__).resolve().parents[2]

    required_docs = [
        repo_root / "docs" / "governance" / "data_lifecycle_policy.md",
        repo_root / "docs" / "governance" / "ai_governance_policy.md",
        repo_root / "docs" / "governance" / "sla_policy.md",
        repo_root / "docs" / "operations" / "operations_manual.md",
        repo_root / "docs" / "governance" / "security_audit_schedule.md",
        repo_root / "docs" / "governance" / "security_audit_report_template.md",
        repo_root / "compliance" / "compliance_checklist.md",
    ]

    for path in required_docs:
        assert path.exists(), f"Missing required governance asset: {path}"


def test_governance_dashboard_interface_exposes_operational_status():
    center = GovernanceCenter()
    payload = center.render()

    assert payload["security"]["latest_audit_time"]
    assert payload["security"]["risk_events"] >= 0
    assert payload["security"]["compliance_status"] == "ready"

    assert payload["data"]["lifecycle_state"] == "active"
    assert payload["data"]["data_usage"] >= 0

    assert payload["operations"]["sla_status"] == "green"
    assert payload["operations"]["service_health"] >= 0

    assert payload["ai"]["model_version"] == "v1"
    assert payload["ai"]["agent_status"] == "online"
