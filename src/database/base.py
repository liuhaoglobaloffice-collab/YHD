"""
Database Base - SQLAlchemy Engine and Session Management

Provides:
- Async database engine
- Async session factory
- Database initialization
- Connection health check
"""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)

# SQLAlchemy Declarative Base
Base = declarative_base()

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """
    Get database URL from configuration.

    Returns:
        Database connection URL
    """
    from ..core.config import get_settings

    settings = get_settings()

    # If direct URL provided, use it
    if settings.database_url:
        url = settings.database_url
        # Convert sync URLs to async
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+aiomysql://", 1)
        elif url.startswith("sqlite://"):
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url

    # Otherwise build from components (PostgreSQL)
    if settings.postgres_host:
        return (
            f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )

    # Default to SQLite for development
    return "sqlite+aiosqlite:///./liuhaos_ai_os.db"


def get_engine() -> AsyncEngine:
    """
    Get or create async database engine.

    Returns:
        AsyncEngine instance
    """
    global _engine

    if _engine is None:
        database_url = get_database_url()

        from ..core.config import get_settings

        settings = get_settings()

        # Determine pooling strategy
        if database_url.startswith("sqlite"):
            # SQLite: Use NullPool (no connection pooling)
            # SQLite: NullPool doesn't support pool configuration
            _engine = create_async_engine(
                database_url,
                poolclass=NullPool,
                echo=getattr(settings, "database_echo", False),
            )
        else:
            # PostgreSQL/MySQL: Use QueuePool with pooling config
            _engine = create_async_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=getattr(settings, "database_pool_size", 5),
                max_overflow=getattr(settings, "database_max_overflow", 10),
                pool_pre_ping=True,  # Verify connections before using
                pool_recycle=3600,  # Recycle connections after 1 hour
                echo=getattr(settings, "database_echo", False),
            )

        # Log connection
        logger.info(
            f"Database engine created: {database_url.split('@')[-1] if '@' in database_url else database_url}"
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get or create async session factory.

    Returns:
        async_sessionmaker instance
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Database session factory created")

    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.

    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...

    Yields:
        AsyncSession instance
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """
    Initialize database schema.

    Creates all tables defined in Base metadata.
    Safe to call multiple times (idempotent).
    """
    engine = get_engine()

    async with engine.begin() as conn:
        # Import all models to register them with Base
        from . import models  # noqa: F401
        # Import provider metrics model so it is registered too
        try:
            from . import provider_metrics_model  # noqa: F401
        except Exception:
            pass

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created/verified")


async def drop_database() -> None:
    """
    Drop all database tables.

    WARNING: Destructive operation. Use only for testing/development.
    """
    engine = get_engine()

    async with engine.begin() as conn:
        from . import models  # noqa: F401

        await conn.run_sync(Base.metadata.drop_all)

        logger.warning("All database tables dropped")


async def check_database_health() -> bool:
    """
    Check database connection health.

    Returns:
        True if database is reachable and healthy
    """
    try:
        engine = get_engine()

        async with engine.connect() as conn:
            # Execute simple query
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))
            return True

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def close_database() -> None:
    """
    Close database engine and clean up connections.

    Should be called on application shutdown.
    """
    global _engine, _session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine closed")
