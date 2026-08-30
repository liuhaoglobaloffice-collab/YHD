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
        # 轻量加列迁移：create_all 只建缺失的表，从不修改已有表。
        # 旧镜像建库的部署会缺列（如 tasks.retry_count），这里按 ORM
        # 元数据自省，对所有方言（SQLite / PostgreSQL）幂等补齐缺失列。
        # 只增不删，绝不触碰已有数据。
        await conn.run_sync(_sync_additive_columns)

        # Failure-recovery on boot: a process restart / container rebuild
        # kills any in-flight workflow executions and tasks mid-run. Without
        # this, rows stay "running" forever and the dashboard reports phantom
        # activity. Mark them as failed so goals can be detected as
        # failed/recovered instead of hanging.
        await conn.execute(
            text(
                "UPDATE workflow_executions "
                "SET status = 'FAILED', error = "
                "COALESCE(error, '') || ' [recovered] interrupted by system restart', "
                "completed_at = CURRENT_TIMESTAMP "
                "WHERE LOWER(status) = 'running' AND completed_at IS NULL"
            )
        )
        await conn.execute(
            text(
                "UPDATE tasks "
                "SET status = 'failed', error = "
                "COALESCE(error, '') || ' [recovered] interrupted by system restart', "
                "completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
                "WHERE LOWER(status) IN ('running', 'in_progress') "
                "AND completed_at IS NULL"
            )
        )
        # Reconcile goals: an active goal whose workflow execution was
        # interrupted by the restart cannot progress anymore — mark it
        # failed so the failure-recovery chain / owner can re-run it
        # instead of showing a forever-"active" phantom.
        await conn.execute(
            text(
                "UPDATE goals "
                "SET status = 'failed', updated_at = CURRENT_TIMESTAMP "
                "WHERE status = 'active' AND workflow_id IS NOT NULL "
                "AND workflow_id IN ("
                "  SELECT workflow_id FROM workflow_executions "
                "  WHERE status = 'FAILED' AND error LIKE '%[recovered]%'"
                ")"
            )
        )
    logger.info("database_tables_created")


def _sync_additive_columns(sync_conn) -> None:
    """Add missing ORM columns to existing tables (additive, idempotent).

    - New tables are already created by ``create_all``.
    - For every existing table, compare DB columns against
      ``Base.metadata``; issue ``ALTER TABLE ADD COLUMN`` for misses.
    - Columns are added as nullable when the model has no server-side
      default (existing rows backfill as NULL; the ORM always supplies
      values on insert, so NOT NULL semantics hold for new writes).
      Models with ``server_default`` keep NOT NULL + DEFAULT.
    """
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(sync_conn)
    dialect_name = sync_conn.dialect.name
    existing_tables = set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {c["name"]: c for c in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in existing_cols:
                # Missing column → ADD COLUMN (nullable; ORM supplies values)
                col_type = column.type.compile(dialect=sync_conn.dialect)
                parts = [f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"]
                if column.server_default is not None:
                    arg = column.server_default.arg
                    default_text = getattr(arg, "text", str(arg))
                    parts.append(f"DEFAULT {default_text}")
                    if not column.nullable:
                        parts.append("NOT NULL")
                ddl = " ".join(parts)
                sync_conn.execute(text(ddl))
                logger.info("migration_add_column", table=table_name, column=column.name)
            elif dialect_name == "postgresql":
                # Widen VARCHAR columns when the ORM declares a larger
                # length (PG enforces VARCHAR(n); older schemas used
                # String(36) for ids that now carry suffixes, e.g.
                # "{uuid}_c0"). SQLite ignores length, so skip there.
                from sqlalchemy import String as SAString

                db_col = existing_cols[column.name]
                db_type = db_col.get("type")
                db_len = getattr(db_type, "length", None)
                orm_len = getattr(column.type, "length", None)
                if (
                    isinstance(column.type, SAString)
                    and orm_len
                    and db_len
                    and orm_len > db_len
                ):
                    sync_conn.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ALTER COLUMN {column.name} TYPE VARCHAR({orm_len})"
                        )
                    )
                    logger.info(
                        "migration_widen_column",
                        table=table_name,
                        column=column.name,
                        old_length=db_len,
                        new_length=orm_len,
                    )


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
