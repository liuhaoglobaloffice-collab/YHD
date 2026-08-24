#!/usr/bin/env python3
"""
重新创建生产环境的 admin 用户（使用正确的 bcrypt 密码哈希）
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.identity.database import init_db, get_session_maker
from src.identity.models import User, RoleEnum
from src.identity.auth import hash_password
from sqlalchemy import select


async def recreate_admin_user():
    """重新创建 admin 用户"""
    print("[STEP 1] 初始化数据库...")
    await init_db()
    
    sm = get_session_maker()
    
    async with sm() as session:
        # 检查是否已存在 admin 用户
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"[STEP 2] 找到现有 admin 用户 (ID={existing_admin.id})")
            print("[STEP 3] 删除现有用户...")
            await session.delete(existing_admin)
            await session.commit()
            print("[OK] 已删除现有 admin 用户")
        else:
            print("[STEP 2] 未找到现有 admin 用户")
        
        # 创建新的 admin 用户（使用正确的 bcrypt 哈希）
        print("[STEP 4] 创建新 admin 用户...")
        password = "admin123"
        hashed_password = hash_password(password)
        
        print(f"[DEBUG] Password: {password}")
        print(f"[DEBUG] Hashed Password: {hashed_password[:50]}...")
        print(f"[DEBUG] Hash starts with '$2b$': {hashed_password.startswith('$2b$')}")
        
        admin = User(
            username="admin",
            hashed_password=hashed_password,
            role=RoleEnum.ADMIN,
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        
        print(f"[OK] Admin 用户创建成功！")
        print(f"     ID: {admin.id}")
        print(f"     Username: {admin.username}")
        print(f"     Role: {admin.role.value}")
        print(f"     Password: {password}")
        print(f"     Active: {admin.is_active}")
        print()
        print("[NEXT] 使用以下信息登录:")
        print(f"       Username: admin")
        print(f"       Password: admin123")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # 确保使用生产环境
    os.environ["APP_ENV"] = "production"
    env_file = Path(__file__).parent / ".env.production"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        print(f"[OK] 已加载生产环境配置")
    else:
        print(f"[ERROR] 找不到 .env.production 文件")
        sys.exit(1)
    
    asyncio.run(recreate_admin_user())
