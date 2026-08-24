"""
Week 3 Day 2 - API集成测试
测试Supplier API的完整HTTP接口
"""

import pytest
import io
from datetime import datetime
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.business.supplier.models import SupplierStatus, BusinessType
from src.identity.models import User


@pytest.fixture
async def test_client(admin_user: User):
    """创建测试客户端"""
    from src.identity.auth import create_access_token
    
    token = create_access_token({"sub": admin_user.username, "role": "admin"})
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"}
    ) as client:
        yield client


class TestSupplierAPIIntegration:
    """Supplier API集成测试"""
    
    @pytest.mark.asyncio
    async def test_create_supplier_api(self, test_client: AsyncClient):
        """测试创建供应商API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        supplier_data = {
            "name": f"API测试供应商-{timestamp}",
            "legal_name": f"API测试供应商有限公司-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 99999}",
            "country": "China",
            "city": "Beijing",
            "address": "北京市朝阳区",
            "business_type": "manufacturer",
                "product_category": "Electronics",
            "product_category": "电子产品",
            "industry": "电子制造",
            "phone": "+86-10-12345678",
            "email": "test@api.com",
        }
        
        response = await test_client.post("/api/v1/suppliers", json=supplier_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == f"API测试供应商-{timestamp}"
        assert data["code"] == f"SUP{int(timestamp[12:]) % 99999}"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_get_supplier_api(self, test_client: AsyncClient):
        """测试获取供应商API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先创建供应商
        create_response = await test_client.post("/api/v1/suppliers", json={
            "name": f"获取测试供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 88888}",
            "country": "China",
            "business_type": "manufacturer",
            "product_category": "Electronics",
        })
        assert create_response.status_code == 201
        supplier_id = create_response.json()["id"]
        
        # 获取供应商
        response = await test_client.get(f"/api/v1/suppliers/{supplier_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == f"获取测试供应商-{timestamp}"
        assert data["code"] == f"SUP{int(timestamp[12:]) % 88888}"
    
    @pytest.mark.asyncio
    async def test_update_supplier_api(self, test_client: AsyncClient):
        """测试更新供应商API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先创建供应商
        create_response = await test_client.post("/api/v1/suppliers", json={
            "name": f"更新测试供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 77777}",
            "country": "China",
            "business_type": "manufacturer",
                "product_category": "Electronics",
        })
        supplier_id = create_response.json()["id"]
        
        # 更新供应商
        update_data = {"country": "USA", "city": "New York"}
        response = await test_client.put(f"/api/v1/suppliers/{supplier_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["country"] == "USA"
        assert data["city"] == "New York"
    
    @pytest.mark.asyncio
    async def test_delete_supplier_api(self, test_client: AsyncClient):
        """测试删除供应商API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先创建供应商
        create_response = await test_client.post("/api/v1/suppliers", json={
            "name": f"删除测试供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 66666}",
            "country": "China",
            "business_type": "manufacturer",
                "product_category": "Electronics",
        })
        supplier_id = create_response.json()["id"]
        
        # 删除供应商
        response = await test_client.delete(f"/api/v1/suppliers/{supplier_id}")
        
        assert response.status_code == 200
        
        # 验证删除
        get_response = await test_client.get(f"/api/v1/suppliers/{supplier_id}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_suppliers_api(self, test_client: AsyncClient):
        """测试列表查询API"""
        # 创建测试数据
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        for i in range(3):
            await test_client.post("/api/v1/suppliers", json={
                "name": f"列表测试供应商{i}-{timestamp}",
                "code": f"SUP{int(timestamp[12:18]) % 9999}{i}",  # 使用完整时间戳+索引
                "country": "China",
                "business_type": "manufacturer",
                "product_category": "Electronics",
            })
        
        # 查询列表
        response = await test_client.get("/api/v1/suppliers?page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 3
    
    @pytest.mark.asyncio
    async def test_search_suppliers_api(self, test_client: AsyncClient):
        """测试搜索API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 创建测试供应商
        await test_client.post("/api/v1/suppliers", json={
            "name": f"搜索特定供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 55555}",
            "country": "China",
            "business_type": "manufacturer",
                "product_category": "Electronics",
        })
        
        # 搜索
        response = await test_client.get("/api/v1/suppliers/search?query=搜索特定")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any("搜索特定" in s["name"] for s in data)


class TestSupplierBatchAPIIntegration:
    """批量操作API集成测试"""
    
    @pytest.mark.asyncio
    async def test_batch_create_api(self, test_client: AsyncClient):
        """测试批量创建API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        import random
        base_num = (int(timestamp[14:]) + random.randint(1000, 9999)) % 99999
        suppliers_data = [
            {
                "name": f"批量API测试{i}-{timestamp}",
                "code": f"SUP{base_num + i}",
                "country": "China",
                "business_type": "manufacturer",
                "product_category": "Electronics",
            }
            for i in range(1, 4)
        ]
        
        response = await test_client.post("/api/v1/suppliers/batch", json=suppliers_data)
        
        assert response.status_code == 201
        data = response.json()
        print(f"Batch create result: {data}")  # Debug
        assert data["success"] == 3
        assert data["failed"] == 0
        assert len(data["ids"]) == 3
    
    @pytest.mark.asyncio
    async def test_batch_update_api(self, test_client: AsyncClient):
        """测试批量更新API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先批量创建
        create_response = await test_client.post("/api/v1/suppliers/batch", json=[
            {
                "name": f"批量更新测试{i}-{timestamp}",
                "code": f"SUP{int(timestamp[12:17]) % 8888}{i}",
                "country": "China",
                "business_type": "manufacturer",
                "product_category": "Electronics",
            }
            for i in range(1, 3)
        ])
        created_ids = create_response.json()["ids"]
        
        # 批量更新
        updates = [{"id": id, "country": "USA"} for id in created_ids]
        response = await test_client.put("/api/v1/suppliers/batch", json=updates)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == 2
        assert data["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_batch_delete_api(self, test_client: AsyncClient):
        """测试批量删除API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先批量创建
        create_response = await test_client.post("/api/v1/suppliers/batch", json=[
            {
                "name": f"批量删除测试{i}-{timestamp}",
                "code": f"SUP{int(timestamp[12:17]) % 7777}{i}",
                "country": "China",
                "business_type": "manufacturer",
                "product_category": "Electronics",
            }
            for i in range(1, 3)
        ])
        created_ids = create_response.json()["ids"]
        
        # 批量删除
        response = await test_client.request("DELETE", "/api/v1/suppliers/batch", json=created_ids)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == 2
        assert data["failed"] == 0


class TestSupplierAdvancedSearchAPIIntegration:
    """高级搜索API集成测试"""
    
    @pytest.mark.asyncio
    async def test_advanced_search_api(self, test_client: AsyncClient):
        """测试高级搜索API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 创建测试数据
        await test_client.post("/api/v1/suppliers/batch", json=[
            {
                "name": f"高级搜索测试{country}{i}-{timestamp}",
                "code": f"SUP{int(timestamp[12:18]) % 8888}{i}",  # 使用完整时间戳+索引
                "country": country,
                "business_type": "manufacturer",
                "product_category": "Electronics",
                "registered_capital": capital,
            }
            for i, (country, capital) in enumerate([
                ("China", 5000000),
                ("China", 10000000),
                ("USA", 15000000),
            ], start=1)
        ])
        
        # 按国家搜索
        response = await test_client.get("/api/v1/suppliers/advanced-search?country=China")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        china_items = [s for s in data["items"] if s["name"].startswith("高级搜索测试China")]
        assert len(china_items) >= 2
    
    @pytest.mark.asyncio
    async def test_advanced_search_with_capital_range_api(self, test_client: AsyncClient):
        """测试按资本范围搜索API"""
        response = await test_client.get(
            "/api/v1/suppliers/advanced-search?"
            "capital_min=5000000&capital_max=10000000"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
        # 验证返回结果在范围内
        for item in data["items"]:
            if item.get("registered_capital"):
                assert 5000000 <= item["registered_capital"] <= 10000000
    
    @pytest.mark.asyncio
    async def test_advanced_search_with_sorting_api(self, test_client: AsyncClient):
        """测试搜索结果排序API"""
        response = await test_client.get(
            "/api/v1/suppliers/advanced-search?"
            "country=China&sort_by=registered_capital&sort_order=desc"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
        # 验证降序排序
        capitals = [
            s["registered_capital"]
            for s in data["items"]
            if s.get("registered_capital") and s["country"] == "China"
        ]
        if len(capitals) > 1:
            assert capitals == sorted(capitals, reverse=True)


class TestSupplierContactAndCertificateAPIIntegration:
    """联系人和证书API集成测试"""
    
    @pytest.mark.asyncio
    async def test_add_contact_api(self, test_client: AsyncClient):
        """测试添加联系人API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先创建供应商
        create_response = await test_client.post("/api/v1/suppliers", json={
            "name": f"联系人测试供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 44444}",
            "country": "China",
            "business_type": "manufacturer",
                "product_category": "Electronics",
        })
        supplier_id = create_response.json()["id"]
        
        # 添加联系人
        contact_data = {
            "name": "测试联系人",
            "position": "经理",
            "phone": "+86-13800138000",
            "email": "contact@test.com",
            "is_primary": True,
        }
        
        response = await test_client.post(
            f"/api/v1/suppliers/{supplier_id}/contacts",
            json=contact_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "测试联系人"
        assert data["is_primary"] is True
    
    @pytest.mark.asyncio
    async def test_add_certificate_api(self, test_client: AsyncClient):
        """测试添加证书API"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        # 先创建供应商
        create_response = await test_client.post("/api/v1/suppliers", json={
            "name": f"证书测试供应商-{timestamp}",
            "code": f"SUP{int(timestamp[12:]) % 33333}",
            "country": "China",
            "business_type": "manufacturer",
                "product_category": "Electronics",
        })
        supplier_id = create_response.json()["id"]
        
        # 添加证书
        certificate_data = {
            "certificate_type": "ISO9001",
            "certificate_name": "ISO 9001:2015",
            "certificate_number": "ISO9001-12345",
            "issuing_authority": "认证机构",
            "issuing_country": "China",
            "issue_date": datetime.utcnow().isoformat(),
            "expiry_date": "2030-01-01T00:00:00",
            "is_verified": True,
        }
        
        response = await test_client.post(
            f"/api/v1/suppliers/{supplier_id}/certificates",
            json=certificate_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "ISO" in data["certificate_type"].upper()


