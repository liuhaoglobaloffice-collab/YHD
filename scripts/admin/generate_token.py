#!/usr/bin/env python3
"""
生成测试用的 JWT token 用于访问 CEO Dashboard
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 设置工作目录为脚本所在目录
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Load environment first
env = os.getenv("APP_ENV", "development")
if env == "production":
    env_file = Path(__file__).parent / ".env.production"
    if env_file.exists():
        load_dotenv(env_file)
else:
    load_dotenv()

import asyncio
from datetime import datetime, timedelta

from src.core.config import get_settings
from src.identity.database import get_session_maker, init_db
from src.identity.models import User
from sqlalchemy import select
import jwt


async def generate_test_token():
    """生成测试 token"""
    await init_db()
    sm = get_session_maker()
    
    config = get_settings()
    
    async with sm() as session:
        # 获取 admin 用户
        result = await session.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("[ERROR] Admin user not found")
            return
        
        # 手动生成 JWT token
        # sub 必须是字符串
        payload = {
            "sub": str(admin.id),  # user_id 作为 sub, 必须是字符串
            "role": admin.role.value,
            "exp": datetime.utcnow() + timedelta(hours=48)  # 48 小时有效期
        }
        
        token = jwt.encode(payload, config.jwt_secret_key, algorithm="HS256")
        
        print(f"[OK] Generated test token for user: {admin.username}")
        print(f"     User ID: {admin.id}")
        print(f"     Role: {admin.role.value}")
        print(f"     Token:")
        print(f"{token}")
        print()
        print(f"Usage:")
        print(f'  curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/ceo/dashboard')
        
        return token


if __name__ == "__main__":
    asyncio.run(generate_test_token())
