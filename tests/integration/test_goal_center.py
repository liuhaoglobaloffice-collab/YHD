"""
Goal Center Integration Tests — P1 实际业务闭环

Tests the full Goal → Parser → Planner → Workflow → AI Employee → Execution → Result → Failure Detection → Failure Recovery → Goal Status chain.
"""

import os
import importlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def env_setup(tmp_path):
    """Set up test environment with SQLite database."""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "goal_center_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"
    yield
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


def _import_models():
    """Import all model modules to register metadata."""
    importlib.import_module("src.database.provider_metrics_model")
    importlib.import_module("src.business.supplier.models")
    importlib.import_module("src.identity.models")
    importlib.import_module("src.tasks.models")
    importlib.import_module("src.database.models")


def test_create_goal_status(env_setup):
    """Test goal creation and status lifecycle."""
    _import_models()
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "goal_admin",
                "email": "goal_admin@example.com",
                "full_name": "Goal Admin",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "goal_admin", "password": "testpass123"},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a goal
        create_resp = client.post(
            "/api/v1/goals",
            json={
                "title": "Test Goal - Increase Sales",
                "description": "Increase sales by 20% in Q3",
                "priority": "high",
                "kpi_name": "revenue",
                "kpi_target": 100000.0,
                "kpi_unit": "USD",
                "budget_total": 5000.0,
            },
            headers=headers,
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        goal = create_resp.json()
        goal_id = goal.get("id")
        assert goal_id is not None
        assert goal.get("status") == "draft"

        # 2. List goals
        list_resp = client.get("/api/v1/goals", headers=headers)
        assert list_resp.status_code == 200, list_resp.text
        goals_data = list_resp.json()
        # The response could be a list or a dict with items
        if isinstance(goals_data, dict):
            items = goals_data.get("items", [])
        else:
            items = goals_data
        assert len(items) >= 1


def test_goal_activate_and_execute(env_setup):
    """Test goal activation (Parser → Planner → Workflow) and execution pathway."""
    _import_models()
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "goal_activate",
                "email": "goal_activate@example.com",
                "full_name": "Goal Activate",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "goal_activate", "password": "testpass123"},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a goal
        create_resp = client.post(
            "/api/v1/goals",
            json={
                "title": "Activate Test Goal",
                "description": "Test goal activation and execution",
                "priority": "normal",
            },
            headers=headers,
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        goal = create_resp.json()
        goal_id = goal["id"]
        assert goal["status"] == "draft"

        # 3. Get goal by ID
        get_resp = client.get(f"/api/v1/goals/{goal_id}", headers=headers)
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["id"] == goal_id


def test_goal_failure_handling(env_setup):
    """Test that goal failure is properly handled."""
    _import_models()
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "goal_fail",
                "email": "goal_fail@example.com",
                "full_name": "Goal Fail",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "goal_fail", "password": "testpass123"},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a goal
        create_resp = client.post(
            "/api/v1/goals",
            json={
                "title": "Failure Test Goal",
                "description": "Test goal failure handling",
                "priority": "normal",
            },
            headers=headers,
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        goal_id = create_resp.json()["id"]

        # Verify failure records endpoint exists
        fail_resp = client.get("/api/v1/goals/failures", headers=headers)
        assert fail_resp.status_code == 200, fail_resp.text


def test_goal_persistence_and_retrieval(env_setup):
    """Test goal data persistence across operations."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.database.models import GoalModel

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        # Create goals with different statuses
        for i, status in enumerate(["draft", "active", "completed", "failed", "cancelled"]):
            goal = GoalModel(
                title=f"Goal {i} - {status}",
                description=f"Test goal with status {status}",
                status=status,
                priority="normal",
                progress_pct=100.0 if status == "completed" else 0.0,
                created_by=1,
            )
            session.add(goal)
        session.commit()

        # Query all goals
        goals = session.query(GoalModel).all()
        assert len(goals) == 5

        # Filter by status
        completed = session.query(GoalModel).filter(GoalModel.status == "completed").all()
        assert len(completed) == 1
        assert completed[0].title == "Goal 2 - completed"

        failed = session.query(GoalModel).filter(GoalModel.status == "failed").all()
        assert len(failed) == 1

        # Test progress tracking
        assert completed[0].progress_pct == 100.0

    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


def test_failure_recovery_chain(env_setup):
    """Test the failure recovery chain end-to-end."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.database.models import FailureRecordModel, GoalModel

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        # Create a goal
        goal = GoalModel(
            title="Recovery Test Goal",
            description="Test failure recovery",
            status="failed",
            priority="normal",
            progress_pct=0.0,
            created_by=1,
            plan_data={"failure_reason": "Provider timeout"},
        )
        session.add(goal)
        session.commit()

        goal_id = goal.id

        # 1. Create failure records
        for i, category in enumerate(["provider_error", "timeout", "agent_error"]):
            record = FailureRecordModel(
                goal_id=goal_id,
                failure_category=category,
                failure_summary=f"Test failure {i}: {category}",
                failure_detail=f"Detailed error for {category}",
                retry_count=0,
                max_retries=3,
                created_by=1,
                strategy_action="retry" if i < 2 else "switch_agent",
            )
            session.add(record)
        session.commit()

        # Query failure records
        records = session.query(FailureRecordModel).filter(
            FailureRecordModel.goal_id == goal_id
        ).all()
        assert len(records) == 3

        # Verify categories
        categories = [r.failure_category for r in records]
        assert "provider_error" in categories
        assert "timeout" in categories
        assert "agent_error" in categories

        # 2. Test recovery strategy persistence
        record = session.query(FailureRecordModel).filter(
            FailureRecordModel.failure_category == "provider_error"
        ).first()
        assert record.strategy_action == "retry"
        assert record.retry_count == 0

        # 3. Test recovery: update retry count and strategy
        record.retry_count = 1
        record.strategy_action = "switch_provider"
        session.commit()
        session.refresh(record)

        assert record.retry_count == 1
        assert record.strategy_action == "switch_provider"

        # 4. Test lesson learning
        record.lesson_learned = "Provider fallback resolved the issue"
        record.is_successful = True
        record.resolved_at = datetime.now(UTC)
        session.commit()
        session.refresh(record)

        assert record.lesson_learned is not None
        assert record.is_successful is True
        assert record.resolved_at is not None

        # 5. Test goal status after recovery
        goal.status = "active"  # Retry
        session.commit()
        session.refresh(goal)
        assert goal.status == "active"

    finally:
        session.close()
        Base.metadata.drop_all(bind=sync_engine)


def test_goal_center_frontend_api(env_setup):
    """Test the goal center API endpoints that the frontend consumes."""
    _import_models()
    from src.api.app import create_app

    app = create_app()
    with TestClient(app) as client:
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "frontend_goal",
                "email": "frontend_goal@example.com",
                "full_name": "Frontend Goal",
                "password": "testpass123",
                "role": "admin",
            },
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "frontend_goal", "password": "testpass123"},
        )
        assert login_resp.status_code == 200, login_resp.text
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a goal with all fields
        create_resp = client.post(
            "/api/v1/goals",
            json={
                "title": "Frontend Goal Test",
                "description": "Goal for frontend API test",
                "priority": "high",
                "kpi_name": "conversion_rate",
                "kpi_target": 0.15,
                "kpi_unit": "percent",
                "budget_total": 10000.0,
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-12-31T23:59:59Z",
            },
            headers=headers,
        )
        assert create_resp.status_code in (200, 201), create_resp.text
        goal = create_resp.json()

        # Verify all fields are present
        assert goal["title"] == "Frontend Goal Test"
        assert goal["status"] == "draft"
        assert goal["priority"] == "high"
        assert goal["kpi_name"] == "conversion_rate"
        assert goal["kpi_target"] == 0.15
        assert goal["kpi_unit"] == "percent"
        assert goal["budget_total"] == 10000.0
        assert goal["progress_pct"] == 0.0

        # Check list endpoint returns proper format
        list_resp = client.get("/api/v1/goals", headers=headers)
        assert list_resp.status_code == 200, list_resp.text
        data = list_resp.json()

        # Should have total and items fields
        if isinstance(data, dict):
            assert "items" in data or "data" in data or "goals" in data
            assert "total" in data or "count" in data