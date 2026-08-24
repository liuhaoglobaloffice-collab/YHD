#!/usr/bin/env python3
"""
创建初始 admin 用户用于测试 CEO Dashboard
"""
import asyncio
import uuid
from datetime import datetime

from src.identity.database import get_session_maker, init_db
from src.identity.models import User, RoleEnum
import hashlib


async def create_admin_user():
    """创建管理员用户"""
    await init_db()
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        # 创建 admin 用户
        admin = User(
            username="admin",
            email="admin@liuhao.ai",
            # 简单哈希用于测试
            hashed_password=hashlib.sha256(b"admin123").hexdigest(),
            role=RoleEnum.ADMIN,
            is_active=True,
            is_superuser=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(admin)
        await session.commit()
        print(f"[OK] Admin user created: {admin.username}")
        print(f"     Email: {admin.email}")
        print(f"     Role: {admin.role.value}")
        print(f"     Password: admin123")
        return admin


if __name__ == "__main__":
    asyncio.run(create_admin_user())
