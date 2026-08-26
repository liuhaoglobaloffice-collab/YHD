"""AI employee center and agent detail scaffolding."""


class AgentCard:
    def __init__(self, name="Research Agent"):
        self.name = name

    def render(self):
        return {"name": self.name, "status": "online", "tasks": 1, "success_rate": 0.96}


class AgentDetails:
    def render(self, agent):
        return {"name": agent.get("name", "Agent"), "status": "online", "capabilities": ["research"]}


class AIEmployeeCenter:
    def load_agents(self):
        return [
            {"name": "Research Agent", "status": "online", "tasks": 1, "success_rate": 0.96, "last_activity": "now"},
            {"name": "Supplier Risk Agent", "status": "online", "tasks": 0, "success_rate": 0.94, "last_activity": "now"},
            {"name": "Sales Agent", "status": "online", "tasks": 1, "success_rate": 0.93, "last_activity": "now"},
            {"name": "Knowledge Agent", "status": "online", "tasks": 2, "success_rate": 0.97, "last_activity": "now"},
            {"name": "Workflow Agent", "status": "online", "tasks": 1, "success_rate": 0.95, "last_activity": "now"},
        ]
