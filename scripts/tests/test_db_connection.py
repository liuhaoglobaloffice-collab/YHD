"""
Test script for Phase 2D-0 Database Foundation verification.
"""

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import (
    init_database,
    check_database_health,
    get_engine,
    get_db_session,
    Base,
)
from src.database.models import (
    DocumentModel,
    MemoryModel,
    CompanyBrainEntityModel,
    WorkflowModel,
    WorkflowExecutionModel,
    TaskModel,
    TaskResultModel,
    AIEmployeeModel,
    EmployeePerformanceModel,
    EmployeeCostModel,
    BusinessTaskModel,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_database_foundation():
    """Test database foundation components."""
    
    print("\n" + "="*60)
    print("Phase 2D-0 Database Foundation Verification")
    print("="*60 + "\n")
    
    # Test 1: Engine creation
    print("[Test 1] Creating database engine...")
    try:
        engine = get_engine()
        print(f"  [PASS] Engine created: {engine.url}")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 2: Table creation
    print("\n[Test 2] Creating database tables...")
    try:
        await init_database()
        print("  [PASS] Tables created successfully")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 3: Health check
    print("\n[Test 3] Database health check...")
    try:
        health = await check_database_health()
        if health:
            print("  [PASS] Database is healthy")
        else:
            print("  [FAIL] Database health check failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 4: Verify all models registered
    print("\n[Test 4] Verifying all models registered...")
    expected_models = {
        "documents": DocumentModel,
        "memories": MemoryModel,
        "company_brain_entities": CompanyBrainEntityModel,
        "workflows": WorkflowModel,
        "workflow_executions": WorkflowExecutionModel,
        "tasks": TaskModel,
        "task_results": TaskResultModel,
        "ai_employees": AIEmployeeModel,
        "employee_performance": EmployeePerformanceModel,
        "employee_costs": EmployeeCostModel,
        "business_tasks": BusinessTaskModel,
    }
    
    registered_tables = {table.name for table in Base.metadata.tables.values()}
    
    for table_name, model_class in expected_models.items():
        if table_name in registered_tables:
            print(f"  [PASS] {table_name} ({model_class.__name__})")
        else:
            print(f"  [FAIL] Missing: {table_name} ({model_class.__name__})")
            return False
    
    # Test 5: Session creation
    print("\n[Test 5] Testing session creation...")
    try:
        session_gen = get_db_session()
        session = await session_gen.__anext__()
        try:
            print(f"  [PASS] Session created: {type(session).__name__}")
        finally:
            try:
                await session_gen.aclose()
            except Exception:
                pass
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 6: Basic CRUD test (Workflow)
    print("\n[Test 6] Testing basic CRUD (WorkflowModel)...")
    try:
        session_gen = get_db_session()
        session = await session_gen.__anext__()
        try:
            # Create
            from datetime import datetime, timezone
            workflow = WorkflowModel(
                id="test-workflow-001",
                name="Test Workflow",
                description="Phase 2D-0 test workflow",
                steps={"step1": "Test step"},
                enabled=True,
                created_by="system",
                created_at=datetime.now(timezone.utc),
            )
            session.add(workflow)
            await session.commit()
            print("  [PASS] CREATE: Workflow created")
            
            # Read
            from sqlalchemy import select
            stmt = select(WorkflowModel).where(WorkflowModel.id == "test-workflow-001")
            result = await session.execute(stmt)
            retrieved = result.scalar_one_or_none()
            if retrieved and retrieved.name == "Test Workflow":
                print("  [PASS] READ: Workflow retrieved")
            else:
                print("  [FAIL] READ: Failed to retrieve workflow")
                return False
            
            # Update
            retrieved.description = "Updated description"
            await session.commit()
            print("  [PASS] UPDATE: Workflow updated")
            
            # Delete
            await session.delete(retrieved)
            await session.commit()
            print("  [PASS] DELETE: Workflow deleted")
        finally:
            try:
                await session_gen.aclose()
            except Exception:
                pass
            
    except Exception as e:
        print(f"  [FAIL] CRUD test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*60)
    print("[SUCCESS] All tests passed!")
    print("="*60 + "\n")
    
    return True


async def main():
    """Main test runner."""
    success = await test_database_foundation()
    
    if success:
        print("\n[SUCCESS] Phase 2D-0 Database Foundation is READY")
        print("[SUCCESS] Can proceed to Phase 2D (Migration Setup)")
        return 0
    else:
        print("\n[FAIL] Phase 2D-0 Database Foundation has issues")
        print("[WARN] Fix issues before proceeding")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
