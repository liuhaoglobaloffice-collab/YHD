"""
Database connection and session management
"""

from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import get_settings
from src.identity.models import Base

logger = structlog.get_logger(__name__)

# Global engine and session maker
_engine = None
_async_session_maker = None


def get_engine():
    """Get or create database engine"""
    global _engine
    if _engine is None:
        settings = get_settings()

        # Convert postgresql:// to postgresql+asyncpg://
        db_url = settings.get_database_url()

        # Convert sqlite:/// to sqlite+aiosqlite:/// for async support
        if db_url.startswith("sqlite:"):
            db_url = db_url.replace("sqlite:", "sqlite+aiosqlite:")

        _engine = create_async_engine(
            db_url,
            echo=settings.app_debug,
            poolclass=NullPool,  # Simple pool for development
        )
        logger.info("database_engine_created")

    return _engine


def get_session_maker():
    """Get or create async session maker"""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("database_session_maker_created")

    return _async_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session (dependency injection for FastAPI)
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database (create tables)"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default data if needed
    await _seed_default_data()

    logger.info("database_initialized")


async def close_db():
    """Close database connections"""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        logger.info("database_closed")
        _engine = None


async def _seed_default_data():
    """
    Seed default roles and permissions if using flexible RBAC
    This is optional for Stage 2 - we can use RoleEnum directly
    or migrate to flexible Role/Permission models later
    """
    # For Stage 2, we keep using RoleEnum in User model
    # Role and Permission tables are created but not actively used yet
    # This allows future migration without breaking existing code
    logger.info("database_seeding_skipped", reason="using_role_enum_for_now")
    pass
