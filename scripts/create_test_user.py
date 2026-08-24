"""
快速创建测试用户
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from src.api.dependencies.database import get_engine
from src.identity.models import User, Base
from src.identity.auth import hash_password
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def create_test_users():
    """创建测试用户"""
    engine = get_engine()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # 测试用户列表
        test_users = [
            {
                "username": "admin",
                "email": "admin@liuhao.ai",
                "full_name": "System Administrator",
                "password": "Admin123!",
                "role": "admin",
            },
            {
                "username": "ceo",
                "email": "ceo@liuhao.ai",
                "full_name": "CEO User",
                "password": "CEO123!",
                "role": "ceo",
            },
            {
                "username": "test",
                "email": "test@liuhao.ai",
                "full_name": "Test User",
                "password": "Test123!",
                "role": "user",
            },
        ]
        
        created_count = 0
        
        for user_data in test_users:
            # Check if exists
            result = await session.execute(
                select(User).where(User.username == user_data["username"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update password
                existing.hashed_password = hash_password(user_data["password"])
                existing.is_active = True
                print(f"✅ 更新用户: {user_data['username']} (密码: {user_data['password']})")
            else:
                # Create new
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    hashed_password=hash_password(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                )
                session.add(user)
                created_count += 1
                print(f"✅ 创建用户: {user_data['username']} (密码: {user_data['password']})")
        
        await session.commit()
        
        # List all users
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        
        print(f"\n📊 数据库用户列表 (共 {len(all_users)} 个):")
        print("-" * 80)
        for user in all_users:
            print(f"ID: {user.id} | 用户名: {user.username:15} | 角色: {user.role:10} | 激活: {user.is_active}")
        print("-" * 80)
        
        print(f"\n✅ 测试用户准备完成！(创建 {created_count} 个，更新 {len(test_users) - created_count} 个)")
        print("\n登录测试:")
        print("  用户名: admin   | 密码: Admin123!")
        print("  用户名: ceo     | 密码: CEO123!")
        print("  用户名: test    | 密码: Test123!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_users())
