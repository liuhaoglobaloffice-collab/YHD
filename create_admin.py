# Create admin user
import asyncio
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.identity.models import User, RoleEnum
from src.identity.auth import hash_password
from src.core.config import get_settings

async def main():
    settings = get_settings()
    db_url = settings.get_database_url().replace("sqlite:///", "sqlite+aiosqlite:///")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Creating admin account...")
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        
        if user:
            user.hashed_password = hash_password("Admin@2026")
            user.is_superuser = True
            user.role = RoleEnum.ADMIN
            await session.commit()
            print(f"Reset admin password to: Admin@2026")
        else:
            user = User(
                username="admin",
                email="admin@liuhao-ai.com",
                full_name="System Administrator",
                hashed_password=hash_password("Admin@2026"),
                role=RoleEnum.ADMIN,
                is_active=True,
                is_superuser=True
            )
            session.add(user)
            await session.commit()
            print("Admin account created!")
            print(f"Username: admin")
            print(f"Password: Admin@2026")

asyncio.run(main())
