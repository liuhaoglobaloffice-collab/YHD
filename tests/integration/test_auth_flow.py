import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.api.schemas import LoginRequest
from src.identity.auth import create_access_token, decode_access_token, hash_password
from src.identity.models import User, RoleEnum, Base


async def _create_test_user_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return async_sessionmaker(engine, expire_on_commit=False)


def test_auth_token_generation_and_decode_round_trip():
    async def _run():
        session_factory = await _create_test_user_session()
        async with session_factory() as session:
            user = User(
                username="phase1user",
                email="phase1@example.com",
                full_name="Phase 1 User",
                hashed_password=hash_password("password123"),
                role=RoleEnum.USER,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            token = create_access_token({"sub": str(user.id), "role": user.role.value})
            payload = decode_access_token(token)
            assert payload.get("sub") == str(user.id)
            assert payload.get("role") == "user"

            # Also verify the requested compatibility alias payload remains parseable.
            request = LoginRequest(username="phase1user", password="password123")
            assert request.username == "phase1user"

    asyncio.run(_run())
