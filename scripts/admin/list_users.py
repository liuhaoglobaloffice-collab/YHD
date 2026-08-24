#!/usr/bin/env python3
import asyncio
from src.identity.database import get_session_maker, init_db
from src.identity.models import User
from sqlalchemy import select


async def list_users():
    await init_db()
    sm = get_session_maker()
    async with sm() as db:
        users = (await db.execute(select(User))).scalars().all()
        print(f"Total users: {len(users)}")
        for u in users:
            print(f"  id={u.id} username={u.username} role={u.role.value}")


asyncio.run(list_users())
