import json
from src.business.supplier.task_adapter import build_task_payload_from_assessment


def test_build_payload_basic():
    assessment = {
        "supplier_id": 10,
        "assessment_id": 99,
        "risk_level": "CRITICAL",
        "overall_score": 20,
        "risk_score": 80,
        "risk_factors": {"financial_score": 20},
        "recommendations": ["Immediate audit", "Hold shipments"],
    }

    payload = build_task_payload_from_assessment(assessment, created_by="tester")
    assert payload["task_type"] == "supplier_risk_review"
    assert "Supplier 10" in payload["title"]
    assert payload["priority"] == "P0"
    assert payload["reference"]["assessment_id"] == 99
    assert payload["created_by"] == "tester"
    assert "Immediate audit" in payload["description"]


def test_build_payload_handles_strings_and_unknown_level():
    assessment = {
        "supplier_id": 11,
        "assessment_id": 100,
        "risk_level": "UNKNOWN",
        "overall_score": "70",
        "risk_score": "30",
        "risk_factors": {"communication_score": "80"},
        "recommendations": "Follow up later",
    }

    payload = build_task_payload_from_assessment(assessment)
    # unknown level defaults to MEDIUM -> P1
    assert payload["priority"] == "P1"
    assert payload["reference"]["supplier_id"] == 11
    # recommendations converted to list and present in description
    assert "Follow up later" in payload["description"]


def test_build_payload_missing_fields_graceful():
    assessment = {"supplier_id": 12}
    payload = build_task_payload_from_assessment(assessment)
    assert payload["reference"]["supplier_id"] == 12
    assert payload["priority"] == "P1"  # default MEDIUM
    assert "Overall Score" in payload["description"]
