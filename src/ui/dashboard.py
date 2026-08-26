"""CEO dashboard and dashboard component cards for the future console."""


class SystemStatusCard:
    def render(self):
        return {"title": "System Status", "value": "online"}


class AIWorkerCard:
    def render(self):
        return {"title": "AI Workers", "value": 3}


class BusinessOverview:
    def render(self):
        return {"title": "Business Overview", "value": "active"}


class RiskMonitor:
    def render(self):
        return {"title": "Risk Monitor", "value": "ok"}


class ActivityTimeline:
    def render(self):
        return {"title": "Activity Timeline", "value": []}


class CEODashboard:
    """Additive dashboard object that mirrors requested CEO visible metrics."""

    def __init__(self):
        self.system_status = {
            "agents": 5,
            "running_tasks": 3,
            "completed_tasks": 12,
            "failed_tasks": 0,
            "pending_approval": 1,
        }
        self.business_status = {
            "customer_opportunities": 4,
            "product_opportunities": 2,
            "supplier_status": "green",
            "risk_alerts": 1,
        }
        self.ai_status = {
            "provider": "ok",
            "local_llm": "ok",
            "api": "ok",
            "plugin": "ok",
            "knowledge_brain": "ok",
        }

    def load(self):
        return {
            "system_status": self.system_status,
            "business_status": self.business_status,
            "ai_status": self.ai_status,
        }
