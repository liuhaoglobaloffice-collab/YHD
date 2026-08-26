"""Workflow templates for the Phase 3 automation demo."""

from typing import Any, Dict, List


class SupplierRiskWorkflowTemplate:
    """Create a deterministic template for the supplier-risk demo workflow."""

    def build(self) -> Dict[str, Any]:
        return {
            "name": "supplier_risk_workflow",
            "steps": [
                {"name": "Risk Assessment", "type": "assessment"},
                {"name": "Create Task", "type": "task"},
                {"name": "Worker Execute", "type": "worker"},
                {"name": "Audit", "type": "audit"},
            ],
            "transitions": [
                {"from": "CREATED", "to": "RUNNING"},
                {"from": "RUNNING", "to": "COMPLETED"},
            ],
            "metadata": {"security_status": "passed"},
        }
