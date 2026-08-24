"""
Week 3 Day 2 - 性能基准测试和并发测试
测试Supplier系统的性能指标和并发处理能力
"""

import pytest
import asyncio
import time
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import Supplier, BusinessType
from src.business.supplier.risk_agent import SupplierRiskAgent


class TestSupplierPerformance:
    """性能基准测试"""
    
    @pytest.mark.asyncio
    async def test_single_supplier_create_performance(self, async_session: AsyncSession):
        """测试单个供应商创建性能"""
        crud = SupplierCRUD(async_session)
        
        supplier_data = {
            "name": "性能测试供应商",
            "code": "SUP9001",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
        }
        
        start_time = time.time()
        supplier = await crud.create_supplier(supplier_data)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        assert supplier.id is not None
        assert elapsed_time < 0.1  # 单个创建应在100ms内完成
        print(f"\n单个供应商创建耗时: {elapsed_time:.4f}秒")
    
    @pytest.mark.asyncio
    async def test_batch_create_performance(self, async_session: AsyncSession):
        """测试批量创建性能"""
        crud = SupplierCRUD(async_session)
        
        # 批量创建100个供应商
        suppliers_data = [
            {
                "name": f"批量性能测试{i}",
                "code": f"SUP90{i:02d}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
            }
            for i in range(10, 110)
        ]
        
        start_time = time.time()
        result = await crud.batch_create(suppliers_data, validate=False)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        throughput = len(suppliers_data) / elapsed_time
        
        assert result["success"] == 100
        assert elapsed_time < 5.0  # 100个供应商应在5秒内完成
        print(f"\n批量创建100个供应商:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  吞吐量: {throughput:.2f} 个/秒")
    
    @pytest.mark.asyncio
    async def test_search_performance(self, async_session: AsyncSession):
        """测试搜索性能"""
        crud = SupplierCRUD(async_session)
        
        # 先创建测试数据
        await crud.batch_create([
            {
                "name": f"搜索性能测试{i}",
                "code": f"SUP91{i:02d}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": i * 1000000,
            }
            for i in range(1, 51)
        ], validate=False)
        
        # 测试简单搜索性能
        start_time = time.time()
        result = await crud.search_suppliers(query="搜索性能", page=1, page_size=20)
        end_time = time.time()
        
        search_time = end_time - start_time
        
        assert len(result) > 0
        assert search_time < 0.5  # 搜索应在500ms内完成
        print(f"\n简单搜索耗时: {search_time:.4f}秒")
    
    @pytest.mark.asyncio
    async def test_advanced_search_performance(self, async_session: AsyncSession):
        """测试高级搜索性能"""
        crud = SupplierCRUD(async_session)
        
        # 测试复杂条件搜索
        start_time = time.time()
        result = await crud.advanced_search(
            filters={
                "country": "China",
                "capital_min": 5000000,
                "capital_max": 30000000,
            },
            sort_by="registered_capital",
            sort_order="desc",
            page=1,
            page_size=20
        )
        end_time = time.time()
        
        search_time = end_time - start_time
        
        assert result["total"] >= 0
        assert search_time < 1.0  # 高级搜索应在1秒内完成
        print(f"\n高级搜索耗时: {search_time:.4f}秒")
    
    @pytest.mark.asyncio
    async def test_risk_assessment_performance(self, async_session: AsyncSession):
        """测试风险评估性能"""
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 创建测试供应商
        supplier = await crud.create_supplier({
            "name": "风险评估性能测试",
            "code": "SUP9501",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
            "registered_capital": 10000000,
        })
        
        # 测试风险评估性能
        start_time = time.time()
        assessment = await risk_agent.assess_risk(supplier_id=supplier.id)
        end_time = time.time()
        
        assessment_time = end_time - start_time
        
        assert assessment is not None
        assert assessment_time < 2.0  # 风险评估应在2秒内完成
        print(f"\n风险评估耗时: {assessment_time:.4f}秒")


class TestSupplierConcurrency:
    """并发测试"""
    
    @pytest.mark.asyncio
    async def test_concurrent_creates(self, async_session: AsyncSession):
        """测试并发创建"""
        crud = SupplierCRUD(async_session)
        
        async def create_supplier(index: int):
            """创建单个供应商"""
            return await crud.create_supplier({
                "name": f"并发测试{index}",
                "code": f"SUP96{index:02d}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
            })
        
        # 并发创建10个供应商
        start_time = time.time()
        tasks = [create_supplier(i) for i in range(1, 11)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # 统计成功数
        success_count = sum(1 for r in results if isinstance(r, Supplier))
        
        assert success_count == 10
        print(f"\n并发创建10个供应商:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  成功: {success_count}/10")
    
    @pytest.mark.asyncio
    async def test_concurrent_reads(self, async_session: AsyncSession):
        """测试并发读取"""
        crud = SupplierCRUD(async_session)
        
        # 先创建测试供应商
        supplier = await crud.create_supplier({
            "name": "并发读取测试",
            "code": "SUP9701",
            "country": "China",
            "business_type": BusinessType.MANUFACTURER,
        })
        
        async def read_supplier():
            """读取供应商"""
            return await crud.get_supplier(supplier.id)
        
        # 并发读取50次
        start_time = time.time()
        tasks = [read_supplier() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # 验证所有读取成功
        success_count = sum(1 for r in results if isinstance(r, Supplier))
        
        assert success_count == 50
        print(f"\n并发读取50次:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  成功: {success_count}/50")
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, async_session: AsyncSession):
        """测试并发更新"""
        crud = SupplierCRUD(async_session)
        
        # 创建测试供应商
        suppliers = []
        for i in range(1, 11):
            supplier = await crud.create_supplier({
                "name": f"并发更新测试{i}",
                "code": f"SUP98{i:02d}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
            })
            suppliers.append(supplier)
        
        async def update_supplier(supplier_id: int, index: int):
            """更新供应商"""
            return await crud.update_supplier(supplier_id, {"city": f"City{index}"})
        
        # 并发更新10个供应商
        start_time = time.time()
        tasks = [update_supplier(s.id, i) for i, s in enumerate(suppliers, 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # 验证所有更新成功
        success_count = sum(1 for r in results if isinstance(r, Supplier))
        
        assert success_count == 10
        print(f"\n并发更新10个供应商:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  成功: {success_count}/10")
    
    @pytest.mark.asyncio
    async def test_concurrent_risk_assessments(self, async_session: AsyncSession):
        """测试并发风险评估"""
        crud = SupplierCRUD(async_session)
        risk_agent = SupplierRiskAgent(async_session)
        
        # 创建测试供应商
        suppliers = []
        for i in range(1, 6):
            supplier = await crud.create_supplier({
                "name": f"并发风险评估{i}",
                "code": f"SUP99{i:02d}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
                "registered_capital": i * 5000000,
            })
            suppliers.append(supplier)
        
        async def assess_supplier(supplier_id: int):
            """评估供应商风险"""
            return await risk_agent.assess_risk(supplier_id=supplier_id)
        
        # 并发评估5个供应商
        start_time = time.time()
        tasks = [assess_supplier(s.id) for s in suppliers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # 验证所有评估成功
        success_count = sum(1 for r in results if isinstance(r, dict) and "risk_level" in r)
        
        assert success_count == 5
        print(f"\n并发风险评估5个供应商:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  成功: {success_count}/5")
    
    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, async_session: AsyncSession):
        """测试混合并发操作（创建、读取、更新）"""
        crud = SupplierCRUD(async_session)
        
        # 先创建10个供应商
        initial_suppliers = []
        for i in range(1, 11):
            supplier = await crud.create_supplier({
                "name": f"混合并发测试{i}",
                "code": f"SUP100{i}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
            })
            initial_suppliers.append(supplier)
        
        async def create_op(index: int):
            return await crud.create_supplier({
                "name": f"混合创建{index}",
                "code": f"SUP101{index}",
                "country": "China",
                "business_type": BusinessType.MANUFACTURER,
            })
        
        async def read_op(supplier_id: int):
            return await crud.get_supplier(supplier_id)
        
        async def update_op(supplier_id: int, index: int):
            return await crud.update_supplier(supplier_id, {"city": f"UpdatedCity{index}"})
        
        # 混合操作：5个创建 + 10个读取 + 5个更新
        tasks = []
        tasks.extend([create_op(i) for i in range(1, 6)])
        tasks.extend([read_op(s.id) for s in initial_suppliers])
        tasks.extend([update_op(initial_suppliers[i].id, i) for i in range(5)])
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        elapsed_time = end_time - start_time
        
        # 验证结果
        success_count = sum(1 for r in results if isinstance(r, Supplier))
        
        assert success_count == 20  # 5创建 + 10读取 + 5更新
        print(f"\n混合并发操作（5创建 + 10读取 + 5更新）:")
        print(f"  总耗时: {elapsed_time:.4f}秒")
        print(f"  成功: {success_count}/20")
