"""
LiuHao AI OS Y1.0
Migration System Test

Tests:
- Database migrations
- Alembic integration
- Schema verification
- Rollback capability
"""

import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.base import get_database_url


@pytest.fixture
def project_root():
    """Get project root directory."""
    root = Path(__file__).parent.parent
    # Load .env for tests
    env_file = root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    return root


def run_alembic_command(command: str, project_root: Path) -> tuple[int, str, str]:
    """Run alembic command and return result."""
    result = subprocess.run(
        ["alembic"] + command.split(), cwd=str(project_root), capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


@pytest.mark.asyncio
async def test_migration_current_version(project_root):
    """Test: Can check current migration version."""
    returncode, stdout, stderr = run_alembic_command("current", project_root)

    assert returncode == 0, f"Alembic current failed: {stderr}"
    assert "83b280b69e5f" in stdout, "Expected migration version not found"


@pytest.mark.asyncio
async def test_migration_history(project_root):
    """Test: Can view migration history."""
    returncode, stdout, stderr = run_alembic_command("history", project_root)

    assert returncode == 0, f"Alembic history failed: {stderr}"
    assert "83b280b69e5f" in stdout, "Initial migration not in history"
    assert "Initial schema - Stage 4-7 models" in stdout


@pytest.mark.asyncio
async def test_database_schema_exists():
    """Test: Database tables exist after migration."""
    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Get inspector
            await conn.run_sync(lambda sync_conn: inspect(sync_conn))

            # Check alembic version table
            tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            assert "alembic_version" in tables, "Alembic version table missing"

            # Check Stage 4 tables
            assert "documents" in tables, "Stage 4: documents table missing"
            assert "memories" in tables, "Stage 4: memories table missing"
            assert "company_brain_entities" in tables, "Stage 4: company_brain_entities missing"

            # Check Stage 5 tables
            assert "workflows" in tables, "Stage 5: workflows table missing"
            assert "workflow_executions" in tables, "Stage 5: workflow_executions missing"
            assert "tasks" in tables, "Stage 5: tasks table missing"
            assert "task_results" in tables, "Stage 5: task_results missing"

            # Check Stage 6 tables
            assert "ai_employees" in tables, "Stage 6: ai_employees table missing"
            assert "employee_performance" in tables, "Stage 6: employee_performance missing"
            assert "employee_costs" in tables, "Stage 6: employee_costs missing"

            # Check Stage 7 tables
            assert "business_tasks" in tables, "Stage 7: business_tasks missing"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migration_downgrade_upgrade(project_root):
    """Test: Can downgrade and re-upgrade migration."""
    # Downgrade
    returncode, stdout, stderr = run_alembic_command("downgrade -1", project_root)
    assert returncode == 0, f"Downgrade failed: {stderr}"

    # Check we're at base
    returncode, stdout, stderr = run_alembic_command("current", project_root)
    assert returncode == 0
    # Should show no current version or empty

    # Upgrade back
    returncode, stdout, stderr = run_alembic_command("upgrade head", project_root)
    assert returncode == 0, f"Upgrade failed: {stderr}"

    # Verify we're at head
    returncode, stdout, stderr = run_alembic_command("current", project_root)
    assert "83b280b69e5f" in stdout, "Not at head after upgrade"


@pytest.mark.asyncio
async def test_alembic_version_tracking():
    """Test: Alembic version is tracked in database."""
    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text("SELECT version_num FROM alembic_version")
            )
            version = result.scalar()

            assert version == "83b280b69e5f", f"Unexpected version: {version}"

    finally:
        await engine.dispose()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
