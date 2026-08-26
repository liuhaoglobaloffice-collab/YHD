from typing import Dict, Optional


class CostManager:
    """In-memory budget and rate-limit manager for provider and LLM usage tracking."""

    def __init__(self, daily_limit: float = 100, monthly_limit: float = 1000, per_agent_limit: float = 50):
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit
        self.per_agent_limit = per_agent_limit
        self.usage: Dict[str, Dict[str, float]] = {}
        self.budget_flags: Dict[str, str] = {}

    def track(self, provider: str, cost: float, agent_id: str) -> Dict[str, str]:
        per_agent = self.usage.setdefault(agent_id, {})
        per_agent[provider] = per_agent.get(provider, 0) + cost
        if per_agent[provider] > self.per_agent_limit:
            self.budget_flags[agent_id] = "limited"
            return {"status": "rate_limited"}
        return {"status": "ok"}

    def apply_budget_policy(self, agent_id: str) -> Dict[str, str]:
        if agent_id in self.budget_flags:
            return {"status": "limited"}
        return {"status": "ok"}

    def budget_status(self, agent_id: str) -> Dict[str, str]:
        if agent_id in self.budget_flags:
            return {"status": "limited"}
        return {"status": "ok"}
