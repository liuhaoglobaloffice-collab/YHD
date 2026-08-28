"""
Database Dependencies - Phase 2F-1

Provides unified async database session management for FastAPI endpoints.

Architecture:
    API Endpoint
        ↓ (Depends)
    get_async_session_dependency()
        ↓
    AsyncSession (per-request)
        ↓ (passed to)
    Service Layer
        ↓
    Repository Layer
        ↓
    Database

Key Features:
- Async session per request
- Automatic transaction management
- Automatic rollback on error
- Session cleanup on completion
- Connection pool management

Security:
- Database URL from environment (Security First)
- No hardcoded credentials
- Connection limits enforced

Usage in API:
    @router.post("/workflows")
    async def create_workflow(
        session: AsyncSession = Depends(get_async_session_dependency),
        current_user: User = Depends(get_current_user),
    ):
        service = WorkflowService(session)
        workflow = await service.create_workflow(...)
        return workflow
"""

from typing import AsyncGenerator

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base, get_database_url

logger = structlog.get_logger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def get_engine():
    """
    Get or create the global async database engine.

    Engine is created once and reused across all requests.
    Connection pooling is handled by SQLAlchemy.
    """
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            future=True,
            pool_pre_ping=True,  # Verify connections before use
            pool_size=10,  # Connection pool size
            max_overflow=20,  # Allow up to 30 connections total
        )
        logger.info(
            "database_engine_created",
            url=database_url.split("@")[-1] if "@" in database_url else "local",
        )
    return _engine


def get_session_factory():
    """
    Get or create the global async session factory.

    Session factory creates new sessions per request.
    """
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Prevent detached instance errors
            autoflush=False,  # Manual flush control
            autocommit=False,  # Manual commit control
        )
        logger.info("database_session_factory_created")
    return _async_session_factory


async def get_async_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database session.

    Provides:
    - New session per request
    - Automatic transaction management
    - Automatic rollback on error
    - Automatic cleanup on completion

    Usage:
        @router.post("/resource")
        async def create_resource(
            session: AsyncSession = Depends(get_async_session_dependency),
        ):
            # Session is automatically managed
            repo = ResourceRepository(session)
            resource = await repo.create(...)
            await session.commit()  # Explicit commit
            return resource

    Error Handling:
        - On exception: session.rollback() called automatically
        - On success: must call session.commit() explicitly
        - On completion: session.close() called automatically

    Yields:
        AsyncSession: Database session for this request
    """
    session_factory = get_session_factory()
    session: AsyncSession = session_factory()

    try:
        logger.debug("database_session_started")
        yield session
        # If we reach here without exception, commit is done by endpoint
        logger.debug("database_session_completed")
    except Exception as e:
        # On any exception, rollback the transaction
        await session.rollback()
        logger.warning(
            "database_session_rolled_back",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise  # Re-raise the exception for FastAPI to handle
    finally:
        # Always close the session
        await session.close()
        logger.debug("database_session_closed")


async def init_database():
    """
    Initialize database tables.

    Creates all tables defined in SQLAlchemy models.
    Should be called during application startup.

    Note: In production, use Alembic migrations instead.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # SQLite 轻量迁移：create_all 不更新已有表，手动补齐新增列
        if engine.dialect.name == "sqlite":
            migrations = {
                "users": {
                    "approval_status": "VARCHAR(20)",
                    "ai_budget_monthly": "FLOAT",
                },
                "leads": {
                    "quote_amount": "FLOAT",
                    "won_amount": "FLOAT",
                    "expected_close_at": "DATETIME",
                    "lost_reason": "VARCHAR(500)",
                },
                "business_tasks": {
                    "owner_user_id": "INTEGER",
                    "created_by": "INTEGER",
                },
            }
            for table, columns in migrations.items():
                cols = [
                    r[1]
                    for r in (
                        await conn.execute(text(f"PRAGMA table_info({table})"))
                    ).fetchall()
                ]
                for col, coltype in columns.items():
                    if col not in cols:
                        await conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                        )
                        logger.info("migration_add_column", table=table, column=col)
    logger.info("database_tables_created")


async def close_database():
    """
    Close database connections.

    Disposes of the engine and closes all connections.
    Should be called during application shutdown.
    """
    global _engine, _async_session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("database_connections_closed")


# Alias for backward compatibility and cleaner imports
get_db = get_async_session_dependency
get_db_session = get_async_session_dependency  # Legacy alias


__all__ = [
    "get_async_session_dependency",
    "get_db",
    "init_database",
    "close_database",
    "get_engine",
    "get_session_factory",
]
