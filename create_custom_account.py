# Create custom admin user
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
        print("=" * 60)
        print("Creating Custom CEO Account")
        print("=" * 60)
        
        # Custom credentials
        username = "1163661699"
        password = "yhd2579..lq"
        
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if user:
            user.hashed_password = hash_password(password)
            user.is_superuser = True
            user.role = RoleEnum.ADMIN
            await session.commit()
            print(f"\n[OK] Account updated: {username}")
        else:
            user = User(
                username=username,
                email="ceo@liuhao-ai.com",
                full_name="CEO",
                hashed_password=hash_password(password),
                role=RoleEnum.ADMIN,
                is_active=True,
                is_superuser=True
            )
            session.add(user)
            await session.commit()
            print(f"\n[OK] Account created!")
        
        print("\n" + "=" * 60)
        print("Login Credentials")
        print("=" * 60)
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"\nAccess URL:")
        print(f"  Frontend: http://localhost:3000")
        print(f"  Command Center: http://localhost:3000/business/supplier/command")
        print("=" * 60)

asyncio.run(main())
