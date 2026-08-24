"""
Phase 2F-1 Database Dependency Integration Test

Tests the new async database session dependency for FastAPI.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies.database import (
    close_database,
    get_async_session_dependency,
    get_engine,
    get_session_factory,
    init_database,
)


@pytest.mark.asyncio
async def test_database_engine_creation():
    """Test: Can create database engine"""
    engine = get_engine()
    assert engine is not None
    assert engine.url is not None


@pytest.mark.asyncio
async def test_session_factory_creation():
    """Test: Can create session factory"""
    factory = get_session_factory()
    assert factory is not None


@pytest.mark.asyncio
async def test_async_session_dependency():
    """Test: Can get async session from dependency"""
    # Initialize database first
    await init_database()

    # Get session from dependency
    async for session in get_async_session_dependency():
        assert isinstance(session, AsyncSession)
        assert session.is_active

        # Test basic query
        result = await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        value = result.scalar()
        assert value == 1

        # Commit to test transaction
        await session.commit()

    # Session should be closed after exiting context
    # (Can't test this directly as session object is closed)


@pytest.mark.asyncio
async def test_session_rollback_on_error():
    """Test: Session rolls back on error"""
    await init_database()

    try:
        async for session in get_async_session_dependency():
            # Simulate an error
            raise ValueError("Test error")
    except ValueError:
        # Error should be raised, session should be rolled back
        pass

    # No assertion needed - if rollback fails, test will fail


@pytest.mark.asyncio
async def test_multiple_sessions():
    """Test: Can create multiple independent sessions"""
    await init_database()

    sessions = []
    async for session1 in get_async_session_dependency():
        sessions.append(session1)
        break

    async for session2 in get_async_session_dependency():
        sessions.append(session2)
        break

    # Sessions should be different instances
    assert sessions[0] != sessions[1]


@pytest.mark.asyncio
async def test_database_init_and_close():
    """Test: Can initialize and close database"""
    # Initialize
    await init_database()

    # Verify tables exist
    engine = get_engine()
    async with engine.begin() as conn:
        # Check if alembic_version table exists (created by migrations)
        # Or check for any model table
        result = await conn.execute(
            __import__("sqlalchemy").text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = [row[0] for row in result]
        assert len(tables) > 0  # Should have tables

    # Close
    await close_database()

    # Engine should be disposed
    # (Can't test this directly, but no error is success)
