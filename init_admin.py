"""快速创建管理员账号"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.identity.models import User, RoleEnum
from src.identity.auth import hash_password

async def create_admin():
    # 使用正确的数据库URL
    db_url = "sqlite+aiosqlite:///./data/liuhao_ai_os.db"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("正在创建管理员账号...")
        
        # 检查是否已存在 admin 账号
        result = await session.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        
        if user:
            # 重置密码
            user.hashed_password = hash_password("Admin2026")
            user.is_superuser = True
            user.role = RoleEnum.ADMIN
            user.is_active = True
            await session.commit()
            print("✅ 管理员账号已重置！")
        else:
            # 创建新账号
            user = User(
                username="admin",
                email="admin@liuhao.com",
                full_name="系统管理员",
                hashed_password=hash_password("Admin2026"),
                role=RoleEnum.ADMIN,
                is_active=True,
                is_superuser=True
            )
            session.add(user)
            await session.commit()
            print("✅ 管理员账号创建成功！")
        
        print("\n=== 登录信息 ===")
        print(f"用户名: admin")
        print(f"密码: Admin2026")
        print("================\n")

if __name__ == "__main__":
    asyncio.run(create_admin())
