"""
P4 产品目录 API 测试.

覆盖产品 CRUD 端点、搜索筛选、分页、权限隔离。
使用内存 SQLite，每次用例独立建库。
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# 注册所有 ORM 模型
import src.database.models  # noqa: F401
import src.identity.models  # noqa: F401
from src.api.app import create_app
from src.api.dependencies.database import get_db
from src.database.base import Base
from src.database.models import ProductModel
from src.identity.database import get_db_session as identity_get_db_session
from src.identity.models import AccountType, User


@pytest_asyncio.fixture
async def session():
    """内存 SQLite 会话：每次用例全新库表。"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session):
    """测试 HTTP 客户端，注入独立内存数据库会话。"""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: session
    # get_current_user 使用 src.identity.database.get_db_session，
    # 需要同步覆盖，确保认证流程也使用内存数据库
    app.dependency_overrides[identity_get_db_session] = lambda: session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(session):
    """创建测试用户（OWNER 类型）。"""
    user = User(
        username="product_test",
        email="product@test.com",
        hashed_password="x",
        account_type=AccountType.OWNER,
        is_active=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    from src.identity.auth import create_access_token

    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


# ==================== CRUD ====================


@pytest.mark.asyncio
async def test_create_product(client, auth_headers):
    payload = {"name": "LED 灯管 60W", "category": "照明", "price": 12.5, "unit": "件", "moq": 100}
    resp = await client.post("/api/v1/products", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "LED 灯管 60W"
    assert data["category"] == "照明"
    assert data["price"] == 12.5
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_product_missing_name_returns_422(client, auth_headers):
    resp = await client.post("/api/v1/products", json={"category": "test"}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_products(client, auth_headers, session, test_user):
    for i in range(3):
        session.add(ProductModel(name=f"产品{i}", category="测试", created_by=test_user.id))
    await session.commit()

    resp = await client.get("/api/v1/products", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_list_products_with_search(client, auth_headers, session, test_user):
    session.add(ProductModel(name="蓝牙耳机", created_by=test_user.id))
    session.add(ProductModel(name="有线耳机", created_by=test_user.id))
    session.add(ProductModel(name="LED 灯管", created_by=test_user.id))
    await session.commit()

    resp = await client.get("/api/v1/products?search=耳机", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_list_products_with_category_filter(client, auth_headers, session, test_user):
    session.add(ProductModel(name="A", category="照明", created_by=test_user.id))
    session.add(ProductModel(name="B", category="电子", created_by=test_user.id))
    await session.commit()

    resp = await client.get("/api/v1/products?category=照明", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "A"


@pytest.mark.asyncio
async def test_get_product_by_id(client, auth_headers, session, test_user):
    p = ProductModel(name="测试产品", price=99.99, created_by=test_user.id)
    session.add(p)
    await session.commit()
    await session.refresh(p)

    resp = await client.get(f"/api/v1/products/{p.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "测试产品"


@pytest.mark.asyncio
async def test_get_product_not_found_returns_404(client, auth_headers):
    resp = await client.get("/api/v1/products/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_product(client, auth_headers, session, test_user):
    p = ProductModel(name="旧名称", price=10.0, created_by=test_user.id)
    session.add(p)
    await session.commit()
    await session.refresh(p)

    resp = await client.put(
        f"/api/v1/products/{p.id}",
        json={"name": "新名称", "price": 20.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名称"
    assert resp.json()["price"] == 20.0


@pytest.mark.asyncio
async def test_delete_product(client, auth_headers, session, test_user):
    p = ProductModel(name="待删除", created_by=test_user.id)
    session.add(p)
    await session.commit()
    await session.refresh(p)

    resp = await client.delete(f"/api/v1/products/{p.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    # 确认已删除
    resp = await client.get(f"/api/v1/products/{p.id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_not_found_returns_404(client, auth_headers):
    resp = await client.delete("/api/v1/products/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_pagination(client, auth_headers, session, test_user):
    for i in range(5):
        session.add(ProductModel(name=f"分页产品{i}", created_by=test_user.id))
    await session.commit()

    resp = await client.get("/api/v1/products?page=1&page_size=2", headers=auth_headers)
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_data_isolation_between_tenants(client, auth_headers, session, test_user):
    """验证不同 Tenant 的 OWNER 数据隔离。

    产品规则：
    - OWNER A（Tenant A）→ 可见 Tenant A 全公司数据
    - OWNER B（Tenant B）→ 可见 Tenant B 全公司数据
    - Tenant A 数据 → OWNER B 不可见
    - Tenant B 数据 → OWNER A 不可见
    """
    tenant_a = "tenant_a_001"
    tenant_b = "tenant_b_002"

    # 给 test_user（OWNER A）设置 tenant_id
    test_user.tenant_id = tenant_a
    session.add(test_user)
    await session.commit()

    # 创建 Tenant A 的产品
    session.add(ProductModel(name="用户A产品", created_by=test_user.id, tenant_id=tenant_a))

    # 创建 OWNER B（不同 Tenant）
    user_b = User(
        username="user_b", email="b@test.com", hashed_password="x",
        is_active=True, account_type=AccountType.OWNER, tenant_id=tenant_b,
    )
    session.add(user_b)
    await session.commit()
    await session.refresh(user_b)
    session.add(ProductModel(name="用户B产品", created_by=user_b.id, tenant_id=tenant_b))
    await session.commit()

    # OWNER A → 只能看到 Tenant A 的数据
    resp = await client.get("/api/v1/products", headers=auth_headers)
    data = resp.json()
    names = [item["name"] for item in data["items"]]
    assert "用户A产品" in names, "OWNER A 应看到自己 Tenant 的产品"
    assert "用户B产品" not in names, "OWNER A 不应看到其他 Tenant 的产品"


@pytest.mark.asyncio
async def test_owner_sees_all_data_in_tenant(client, auth_headers, session, test_user):
    """验证同一个 Tenant 内，OWNER 对公司数据具有全局可见权限。"""
    tenant_id = "tenant_global_test"

    test_user.tenant_id = tenant_id
    session.add(test_user)
    await session.commit()

    # 同一个 Tenant 内多个用户的数据
    session.add(ProductModel(name="产品A-销售创建", created_by=test_user.id, tenant_id=tenant_id))
    coworker = User(
        username="coworker", email="coworker@test.com", hashed_password="x",
        is_active=True, account_type=AccountType.OWNER, tenant_id=tenant_id,
    )
    session.add(coworker)
    await session.commit()
    await session.refresh(coworker)
    session.add(ProductModel(name="产品B-同事创建", created_by=coworker.id, tenant_id=tenant_id))
    await session.commit()

    # OWNER 应看到 Tenant 内所有产品（包括同事创建的）
    resp = await client.get("/api/v1/products", headers=auth_headers)
    data = resp.json()
    names = [item["name"] for item in data["items"]]
    assert "产品A-销售创建" in names, "OWNER 应看到自己创建的产品"
    assert "产品B-同事创建" in names, "OWNER 应看到同 Tenant 同事创建的产品"


@pytest.mark.asyncio
async def test_filter_by_status(client, auth_headers, session, test_user):
    session.add(ProductModel(name="上架产品", status="active", created_by=test_user.id))
    session.add(ProductModel(name="下架产品", status="inactive", created_by=test_user.id))
    await session.commit()

    resp = await client.get("/api/v1/products?status=active", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "上架产品"

    resp = await client.get("/api/v1/products?status=inactive", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "下架产品"