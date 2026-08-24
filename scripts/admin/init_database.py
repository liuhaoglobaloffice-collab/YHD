"""
Database initialization script for LiuHao AI OS Y1.0
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load production environment
env_file = Path(__file__).parent / ".env.production"
if env_file.exists():
    load_dotenv(env_file)

from src.identity.database import init_db, get_engine
from src.identity.models import Base
import structlog

logger = structlog.get_logger(__name__)


async def init_database():
    """Initialize database schema"""
    print("=" * 60)
    print("[DB INIT] Initializing LiuHao AI OS Database")
    print("=" * 60)
    
    try:
        # Get database engine
        engine = get_engine()
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("[OK] Database schema created successfully")
        
        # Initialize default data
        await init_db()
        
        print("[OK] Default data initialized")
        print("=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(init_database())

