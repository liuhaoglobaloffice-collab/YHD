import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.identity.models import User
from src.core.config import get_settings

async def check():
    settings = get_settings()
    db_url = settings.get_database_url().replace('sqlite:///', 'sqlite+aiosqlite:///')
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Checking user account...")
        print("=" * 60)
        
        # Check specific user
        result = await session.execute(select(User).where(User.username == '1163661699'))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"[OK] User found!")
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Full Name: {user.full_name}")
            print(f"  Active: {user.is_active}")
            print(f"  Superuser: {user.is_superuser}")
            print(f"  Role: {user.role}")
        else:
            print("[ERROR] User not found!")
            
        # List all users
        print("\n" + "=" * 60)
        print("All users in database:")
        print("=" * 60)
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        for u in all_users:
            print(f"  - {u.username} ({u.email}) - Active: {u.is_active}, Superuser: {u.is_superuser}")

asyncio.run(check())
