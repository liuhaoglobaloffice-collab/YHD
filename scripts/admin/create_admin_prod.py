#!/usr/bin/env python3
"""
快速创建生产环境管理员用户
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load production env
load_dotenv(Path(__file__).parent / ".env.production")

import asyncio
from src.identity.database import get_session_maker, init_db
from src.identity.models import User, RoleEnum
from sqlalchemy import select
from datetime import datetime
import hashlib

async def create_admin():
    """创建管理员用户"""
    await init_db()
    sm = get_session_maker()
    
    async with sm() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"[OK] Admin user already exists: ID={user.id}, username={user.username}")
            return
        
        # Create admin
        user = User(
            username="admin",
            email="admin@liuhao.ai",
            hashed_password=hashlib.sha256("admin123".encode()).hexdigest(),
            role=RoleEnum.ADMIN,
            is_active=True,
            is_superuser=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        print(f"[OK] Created admin user: ID={user.id}, username={user.username}")

if __name__ == "__main__":
    asyncio.run(create_admin())
