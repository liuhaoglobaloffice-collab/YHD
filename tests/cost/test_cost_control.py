from src.cost.cost_manager import CostManager


def test_cost_manager_checks_budget_and_rate_limit():
    manager = CostManager(daily_limit=100, monthly_limit=1000, per_agent_limit=50)
    assert manager.track("openai", 10, "agent-a") == {"status": "ok"}
    assert manager.track("openai", 60, "agent-a") == {"status": "rate_limited"}

    manager.apply_budget_policy("agent-a")
    assert manager.budget_status("agent-a")["status"] in {"ok", "limited"}
