"""Task and workflow console scaffolding."""


class TaskWorkflowConsole:
    def load_task(self, task_id):
        return {
            "task_id": task_id,
            "type": "supplier_risk",
            "status": "COMPLETED",
            "priority": "high",
            "execution_time": "00:12:03",
            "worker": "risk_agent",
            "workflow_status": "COMPLETED",
            "failure_reason": None,
            "audit_record": "created",
        }
