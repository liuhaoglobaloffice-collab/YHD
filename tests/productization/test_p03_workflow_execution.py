from pathlib import Path


def test_workflow_execution_contract_exists():
    root = Path(__file__).resolve().parents[2]
    route = root / "src" / "api" / "routes" / "productization.py"
    task_service = root / "src" / "tasks" / "service.py"
    workflow_executor = root / "src" / "workflow" / "executor.py"

    assert route.exists(), "Missing productization route"
    assert task_service.exists(), "Missing task service"
    assert workflow_executor.exists(), "Missing workflow executor"

    route_text = route.read_text(encoding="utf-8")
    task_text = task_service.read_text(encoding="utf-8")
    workflow_text = workflow_executor.read_text(encoding="utf-8")

    assert "TaskService" in route_text
    assert "AuditService" in route_text
    assert "class TaskService" in task_text
    assert "class WorkflowExecutor" in workflow_text
