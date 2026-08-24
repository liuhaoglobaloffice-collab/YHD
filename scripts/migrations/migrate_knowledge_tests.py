#!/usr/bin/env python3
"""
LiuHao AI OS Y1.0
Phase 4 Module 1 - Knowledge Tests Migration Script

Update test fixtures to use AsyncSession + new service constructors.
"""

import re


def migrate_tests():
    """Migrate test fixtures to use database-backed services"""
    
    # 1. Fix test_company_brain.py
    file_path = "tests/test_knowledge/test_company_brain.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(file_path + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    
    # Add async session fixture imports at top
    import_pattern = r'(import pytest\n)'
    import_addition = r'''\1import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

'''
    content = re.sub(import_pattern, import_addition, content)
    
    # Add async session fixture
    session_fixture = '''

@pytest_asyncio.fixture
async def async_session():
    """Test database session"""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    from src.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


'''
    
    # Insert after mock_audit fixture
    audit_fixture_end = content.find("@pytest.fixture\ndef company_brain")
    if audit_fixture_end > 0:
        content = content[:audit_fixture_end] + session_fixture + content[audit_fixture_end:]
    
    # Update company_brain fixture to use async_session
    old_brain_fixture = r'''@pytest\.fixture
def company_brain\(mock_rbac, mock_audit\):
    """Company brain fixture"""
    return CompanyBrain\(
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    \)'''
    
    new_brain_fixture = '''@pytest_asyncio.fixture
async def company_brain(async_session, mock_rbac, mock_audit):
    """Company brain fixture"""
    return CompanyBrain(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )'''
    
    content = re.sub(old_brain_fixture, new_brain_fixture, content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] test_company_brain.py migrated to async fixtures")
    
    # 2. Fix test_memory.py
    file_path = "tests/test_knowledge/test_memory.py"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(file_path + ".bak", "w", encoding="utf-8") as f:
        f.write(content)
    
    # Add async session fixture imports
    import_pattern = r'(import pytest\n)'
    import_addition = r'''\1import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

'''
    content = re.sub(import_pattern, import_addition, content)
    
    # Add async session fixture
    session_fixture = '''

@pytest_asyncio.fixture
async def async_session():
    """Test database session"""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create tables
    from src.database.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
    
    await engine.dispose()


'''
    
    # Insert after mock_audit fixture
    audit_fixture_end = content.find("@pytest.fixture\ndef memory_service")
    if audit_fixture_end > 0:
        content = content[:audit_fixture_end] + session_fixture + content[audit_fixture_end:]
    
    # Update memory_service fixture
    old_memory_fixture = r'''@pytest\.fixture
def memory_service\(mock_rbac, mock_audit\):
    """Memory service fixture"""
    return MemoryService\(
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    \)'''
    
    new_memory_fixture = '''@pytest_asyncio.fixture
async def memory_service(async_session, mock_rbac, mock_audit):
    """Memory service fixture"""
    return MemoryService(
        session=async_session,
        rbac_service=mock_rbac,
        audit_service=mock_audit,
    )'''
    
    content = re.sub(old_memory_fixture, new_memory_fixture, content)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("[OK] test_memory.py migrated to async fixtures")
    
    print("\n[OK] All knowledge tests migrated to database fixtures")
    print("  - Added async_session fixtures")
    print("  - Updated service constructors")
    print("  - Services now use in-memory SQLite for tests")


if __name__ == "__main__":
    migrate_tests()
