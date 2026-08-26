import json
from typing import Dict, Any, List


def _normalize_risk_level(value: Any) -> str:
    if value is None:
        return "MEDIUM"
    try:
        v = str(value).upper()
    except Exception:
        return "MEDIUM"
    mapping = {"VERY_LOW": "VERY_LOW", "LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH", "CRITICAL": "CRITICAL"}
    return mapping.get(v, "MEDIUM")


def _to_float(value: Any, default: float = 50.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _derive_priority_from_level(level: str) -> str:
    if level == "CRITICAL":
        return "P0"
    if level == "HIGH":
        return "P0"
    if level == "MEDIUM":
        return "P1"
    return "P2"


def build_task_payload_from_assessment(assessment: Dict[str, Any], created_by: str = "system") -> Dict[str, Any]:
    """
    Build a task payload dict from a normalized supplier risk assessment dict.

    Expected assessment keys (best-effort):
      - supplier_id
      - assessment_id
      - risk_level
      - overall_score
      - risk_score
      - risk_factors (dict)
      - recommendations (list)

    Returns a dict with keys:
      - task_type
      - title
      - description
      - priority
      - reference (dict)
      - created_by
    """
    supplier_id = assessment.get("supplier_id")
    assessment_id = assessment.get("assessment_id")
    risk_level = _normalize_risk_level(assessment.get("risk_level"))
    overall_score = _to_float(assessment.get("overall_score", 50.0))
    risk_score = _to_float(assessment.get("risk_score", max(0.0, 100.0 - overall_score)))

    risk_factors = assessment.get("risk_factors") or {}
    try:
        rf_pretty = json.dumps(risk_factors, ensure_ascii=False)
    except Exception:
        rf_pretty = str(risk_factors)

    recommendations = assessment.get("recommendations")
    if recommendations is None:
        recommendations = []
    if not isinstance(recommendations, list):
        recommendations = [str(recommendations)]

    title = f"Review Risk Assessment for Supplier {supplier_id} (Level {risk_level})"

    desc_lines: List[str] = []
    desc_lines.append(f"Overall Score: {overall_score}")
    desc_lines.append(f"Risk Score: {risk_score}")
    desc_lines.append(f"Risk Level: {risk_level}")
    desc_lines.append("Risk Factors:")
    desc_lines.append(rf_pretty)
    if recommendations:
        desc_lines.append("Recommendations:")
        for r in recommendations:
            desc_lines.append(f"- {r}")

    description = "\n".join(desc_lines)

    payload = {
        "task_type": "supplier_risk_review",
        "title": title,
        "description": description,
        "priority": _derive_priority_from_level(risk_level),
        "reference": {
            "assessment_id": assessment_id,
            "supplier_id": supplier_id,
        },
        "created_by": created_by,
    }

    return payload
