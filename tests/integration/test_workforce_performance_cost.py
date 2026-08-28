"""
Workforce Performance and Cost Integration Tests — P1 实际业务闭环

Tests that the workforce performance and cost endpoints return real data instead of placeholders:
- /workforce/employees/{id}/performance: returns real task statistics from BusinessTaskModel
- /workforce/employees/{id}/cost: returns real cost statistics from AiCostRecordModel
"""

import os
import importlib
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def env_setup(tmp_path):
    """Set up test environment with SQLite database."""
    os.environ["METRICS_PERSIST"] = "0"
    db_file = tmp_path / "workforce_test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file.as_posix()}"

    # Reset cached singletons
    import sys
    from src.ceo.dashboard import reset_ceo_dashboard
    reset_ceo_dashboard()

    _dep_mod = sys.modules.get("src.api._dependencies_module")
    if _dep_mod:
        _dep_mod._employee_registry = None
        _dep_mod._employee_service = None
        _dep_mod._lifecycle_manager = None
        _dep_mod._performance_tracker = None
        _dep_mod._cost_tracker = None
        _dep_mod._business_service = None

    import src.identity.database as ident_db_mod
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None

    yield

    reset_ceo_dashboard()
    _dep_mod2 = sys.modules.get("src.api._dependencies_module")
    if _dep_mod2:
        _dep_mod2._employee_registry = None
        _dep_mod2._employee_service = None
        _dep_mod2._lifecycle_manager = None
        _dep_mod2._performance_tracker = None
        _dep_mod2._cost_tracker = None
        _dep_mod2._business_service = None
    ident_db_mod._engine = None
    ident_db_mod._async_session_maker = None
    os.environ.pop("METRICS_PERSIST", None)
    os.environ.pop("DATABASE_URL", None)


def _import_models():
    """Import all model modules to register metadata."""
    importlib.import_module("src.database.provider_metrics_model")
    importlib.import_module("src.business.supplier.models")
    importlib.import_module("src.identity.models")
    importlib.import_module("src.tasks.models")
    importlib.import_module("src.database.models")


def _register_and_login(client, username="testuser"):
    """Register and login a test user, returning auth headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": username,
            "password": "testpass123",
            "role": "admin",
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "testpass123"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_workforce_performance_endpoint_returns_real_data(env_setup):
    """Test that performance endpoint returns real task statistics from database."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.database.models import BusinessTaskModel, AiCostRecordModel, AIEmployeeModel
    from src.identity.models import User
    from src.workforce.models import AIEmployeeStatus, Department, Position
    from src.api.app import create_app

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        # Create user
        user = User(
            id=1000,
            username="perf_user",
            email="perf_user@example.com",
            hashed_password="fakehash",
            role="admin",
            account_type="owner",
        )
        session.add(user)
        session.commit()

        # Create AI employee
        employee_id = uuid4()
        employee = AIEmployeeModel(
            id=str(employee_id),
            name="Test Analyst",
            department=Department.ANALYTICS.value,
            position=Position.BUSINESS_ANALYST.value,
            description="Test business analyst",
            status="active",
        )
        session.add(employee)
        session.commit()

        employee_id_str = str(employee_id)

        # Create completed tasks
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        for i in range(2):
            task = BusinessTaskModel(
                id=str(uuid4()),
                domain="analysis",
                title=f"Completed Task {i}",
                description="Test completed task",
                status="completed",
                priority="medium",
                assigned_employee_id=employee_id_str,
                assigned_by=str(user.id),
                created_at=now - timedelta(hours=2),
                completed_at=now - timedelta(hours=1),
                owner_user_id=user.id,
            )
            session.add(task)

        # Create failed task
        failed_task = BusinessTaskModel(
            id=str(uuid4()),
            domain="analysis",
            title="Failed Task",
            description="Test failed task",
            status="failed",
            priority="medium",
            assigned_employee_id=employee_id_str,
            assigned_by=str(user.id),
            created_at=now - timedelta(hours=1),
            completed_at=None,
            owner_user_id=user.id,
        )
        session.add(failed_task)
        session.commit()

        # Verify data
        completed = session.query(BusinessTaskModel).filter(
            BusinessTaskModel.assigned_employee_id == employee_id_str,
            BusinessTaskModel.status == "completed",
        ).count()
        assert completed == 2, f"Expected 2 completed, got {completed}"

        failed = session.query(BusinessTaskModel).filter(
            BusinessTaskModel.assigned_employee_id == employee_id_str,
            BusinessTaskModel.status == "failed",
        ).count()
        assert failed == 1, f"Expected 1 failed, got {failed}"

    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        headers = _register_and_login(client, "perf_test_user")

        response = client.get(f"/api/v1/workforce/employees/{employee_id_str}/performance", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["employee_id"] == employee_id_str
        assert data["tasks_completed"] == 2
        assert data["tasks_failed"] == 1
        assert data["success_rate"] == pytest.approx(0.67, 0.01)
        assert data["total_execution_time"] > 0
        assert data["average_execution_time"] > 0
        print(f"✓ Performance data: {data}")

    Base.metadata.drop_all(bind=sync_engine)


def test_workforce_cost_endpoint_returns_real_data(env_setup):
    """Test that cost endpoint returns real cost statistics from database."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.database.models import AiCostRecordModel, AIEmployeeModel
    from src.identity.models import User
    from src.workforce.models import Department, Position
    from src.api.app import create_app

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        # Create user
        user = User(
            id=2000,
            username="cost_user",
            email="cost_user@example.com",
            hashed_password="fakehash",
            role="admin",
            account_type="owner",
        )
        session.add(user)
        session.commit()

        # Create AI employee
        employee_id = uuid4()
        employee_id_str = str(employee_id)
        employee = AIEmployeeModel(
            id=str(employee_id),
            name="Test AI Employee",
            department=Department.MARKETING.value,
            position=Position.CONTENT_WRITER.value,
            description="Test content writer",
            status="active",
        )
        session.add(employee)
        session.commit()

        # Create cost records
        for rec_data in [
            ("openai", "gpt-4o-mini", 500, 1500, 2000, 0.0003, "success"),
            ("openai", "gpt-4o-mini", 800, 2200, 3000, 0.00045, "success"),
            ("openai", "gpt-4o-mini", 300, 0, 300, 0.000045, "failed"),
        ]:
            rec = AiCostRecordModel(
                user_id=user.id,
                employee_id=employee_id_str,
                agent_type="content_writer",
                provider=rec_data[0],
                model=rec_data[1],
                input_tokens=rec_data[2],
                output_tokens=rec_data[3],
                total_tokens=rec_data[4],
                cost_usd=rec_data[5],
                latency_ms=1000.0,
                status=rec_data[6],
            )
            session.add(rec)
        session.commit()

        # Verify data
        count = session.query(AiCostRecordModel).filter(
            AiCostRecordModel.employee_id == employee_id_str,
        ).count()
        assert count == 3, f"Expected 3 records, got {count}"

    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        headers = _register_and_login(client, "cost_test_user")

        response = client.get(f"/api/v1/workforce/employees/{employee_id_str}/cost", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["employee_id"] == employee_id_str
        assert data["api_calls"] == 3
        assert data["tokens_used"] == 2000 + 3000 + 300
        assert data["total_cost_usd"] == pytest.approx(0.0003 + 0.00045 + 0.000045)
        print(f"✓ Cost data: {data}")

    Base.metadata.drop_all(bind=sync_engine)


def test_workforce_performance_empty_data(env_setup):
    """Test performance endpoint with no tasks returns zeros correctly."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.identity.models import User
    from src.database.models import AIEmployeeModel
    from src.workforce.models import Department, Position
    from src.api.app import create_app

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        user = User(
            id=3000,
            username="empty_user",
            email="empty_user@example.com",
            hashed_password="fakehash",
            role="admin",
            account_type="owner",
        )
        session.add(user)
        session.commit()

        employee_id = uuid4()
        employee_id_str = str(employee_id)
        employee = AIEmployeeModel(
            id=str(employee_id),
            name="Empty Employee",
            department=Department.ANALYTICS.value,
            position=Position.BUSINESS_ANALYST.value,
            description="No tasks yet",
            status="active",
        )
        session.add(employee)
        session.commit()
    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        headers = _register_and_login(client, "empty_test_user")

        response = client.get(f"/api/v1/workforce/employees/{employee_id_str}/performance", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tasks_completed"] == 0
        assert data["tasks_failed"] == 0
        assert data["success_rate"] == 0.0
        assert data["total_execution_time"] == 0.0
        assert data["average_execution_time"] == 0.0
        print("✓ Empty performance data handled correctly")

    Base.metadata.drop_all(bind=sync_engine)


def test_workforce_cost_empty_data(env_setup):
    """Test cost endpoint with no records returns zeros correctly."""
    _import_models()
    import sqlalchemy as sa
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from src.database.base import Base
    from src.identity.models import User
    from src.database.models import AIEmployeeModel
    from src.workforce.models import Department, Position
    from src.api.app import create_app

    db_url = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    sync_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=sync_engine)

    SyncSession = sessionmaker(bind=sync_engine)
    session = SyncSession()

    try:
        user = User(
            id=4000,
            username="cost_empty_user",
            email="cost_empty_user@example.com",
            hashed_password="fakehash",
            role="admin",
            account_type="owner",
        )
        session.add(user)
        session.commit()

        employee_id = uuid4()
        employee_id_str = str(employee_id)
        employee = AIEmployeeModel(
            id=str(employee_id),
            name="New Employee",
            department=Department.ANALYTICS.value,
            position=Position.BUSINESS_ANALYST.value,
            description="No cost records yet",
            status="active",
        )
        session.add(employee)
        session.commit()
    finally:
        session.close()

    app = create_app()
    with TestClient(app) as client:
        headers = _register_and_login(client, "cost_empty_test")

        response = client.get(f"/api/v1/workforce/employees/{employee_id_str}/cost", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["api_calls"] == 0
        assert data["tokens_used"] == 0
        assert data["total_cost_usd"] == 0.0
        print("✓ Empty cost data handled correctly")

    Base.metadata.drop_all(bind=sync_engine)