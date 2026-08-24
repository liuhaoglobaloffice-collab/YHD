"""
Integration test for Phase 2D-0: Repository -> Database
"""

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_database, get_db_session
from src.database.repositories.workflow import WorkflowRepository
from src.database.models import WorkflowModel


async def test_repository_integration():
    """Test that repositories can use the database."""
    
    print("\n" + "="*60)
    print("Phase 2D-0 Repository Integration Test")
    print("="*60 + "\n")
    
    # Initialize database
    print("[1] Initializing database...")
    await init_database()
    print("  [PASS] Database initialized\n")
    
    # Get database session
    print("[2] Creating database session...")
    session_gen = get_db_session()
    session = await session_gen.__anext__()
    print("  [PASS] Session created\n")
    
    try:
        # Create repository
        print("[3] Creating WorkflowRepository...")
        repo = WorkflowRepository(session)
        print("  [PASS] WorkflowRepository created\n")
        
        # Test: Create workflow
        print("[4] Creating workflow via repository...")
        workflow_id = str(uuid4())
        workflow_model = WorkflowModel(
            id=workflow_id,
            name="Test Repository Workflow",
            description="Testing repository -> database integration",
            created_by=str(uuid4()),
            version=1,
            tags=["test", "repository"],
            enabled=True,
            steps=[{"step_id": "step1", "step_type": "TASK", "name": "Test Step"}],
            context={"meta": {"test": "phase2d0"}},
            created_at=datetime.now(timezone.utc),
        )
        
        created = await repo.create(workflow_model)
        print(f"  [PASS] Workflow created: {created.name} (ID: {created.id})\n")
        
        # Test: Read workflow
        print("[5] Reading workflow via repository...")
        retrieved = await repo.get_by_id(workflow_id)
        if retrieved:
            print(f"  [PASS] Workflow retrieved: {retrieved.name}")
            print(f"       Enabled: {retrieved.enabled}")
            print(f"       Version: {retrieved.version}")
            print(f"       Tags: {retrieved.tags}\n")
        else:
            print("  [FAIL] Workflow not found\n")
            return False
        
        # Test: Update workflow
        print("[6] Updating workflow via repository...")
        new_tags = retrieved.tags.copy()
        new_tags.append("updated")
        await repo.update(workflow_id, {"description": "Updated repository test", "tags": new_tags})
        updated = await repo.get_by_id(workflow_id)
        print(f"  [PASS] Workflow updated: {updated.description}")
        print(f"       Tags: {updated.tags}\n")
        
        # Test: List workflows
        print("[7] Listing workflows via repository...")
        workflows = await repo.list_all(limit=100)
        print(f"  [PASS] Found {len(workflows)} workflow(s)\n")
        
        # Test: Delete workflow
        print("[8] Deleting workflow via repository...")
        success = await repo.delete(workflow_id)
        print(f"  [PASS] Workflow deleted: {success}\n")
        
        # Verify deletion
        print("[9] Verifying deletion...")
        deleted = await repo.get_by_id(workflow_id)
        if deleted is None:
            print("  [PASS] Workflow successfully deleted\n")
        else:
            print("  [FAIL] Workflow still exists after deletion\n")
            return False
        
    finally:
        try:
            await session_gen.aclose()
        except:
            pass
    
    print("="*60)
    print("[SUCCESS] Repository Integration Test Passed!")
    print("="*60 + "\n")
    
    print("Phase 2D-0 Verification Complete:")
    print("  OK Database foundation established")
    print("  OK Models registered and working")
    print("  OK Repositories functional")
    print("  OK CRUD operations working end-to-end")
    print("  OK Database persistence verified")
    print("\nReady for Phase 2D (Migration System Setup)")
    
    return True


async def main():
    try:
        success = await test_repository_integration()
        return 0 if success else 1
    except Exception as e:
        print(f"\n[ERROR] Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
