"""Get auth token for testing."""
import asyncio
import httpx

async def main():
    r = await httpx.AsyncClient().post(
        "http://localhost:8001/api/v1/auth/login",
        json={"username": "testuser2", "password": "testpass123"},
    )
    d = r.json()
    token = d.get("access_token", "")
    print(token)

asyncio.run(main())