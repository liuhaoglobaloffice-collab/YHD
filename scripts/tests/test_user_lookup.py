#!/usr/bin/env python3
import asyncio
from src.identity.database import get_session_maker, init_db
from src.identity.models import User
from sqlalchemy import select


async def test_user_lookup():
    await init_db()
    sm = get_session_maker()
    
    user_id = 1
    
    async with sm() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        print(f"Looking for user_id: {user_id} (type: {type(user_id)})")
        
        if user:
            print(f"Found user: {user.username}")
            print(f"  ID: {user.id}")
            print(f"  Role: {user.role.value}")
            print(f"  Active: {user.is_active}")
        else:
            print("User NOT found")
            
            # 列出所有用户
            all_users = (await session.execute(select(User))).scalars().all()
            print(f"\nAll users in database: {len(all_users)}")
            for u in all_users:
                print(f"  - ID={u.id} username={u.username}")


asyncio.run(test_user_lookup())
