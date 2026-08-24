"""
测试 Supplier 模块
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.modules.supplier_module import SupplierModule
from src.core.modules import ModuleStatus


class TestSupplierModule:
    """测试 Supplier 模块"""
    
    def test_module_info(self):
        """测试模块信息"""
        module = SupplierModule()
        info = module.get_module_info()
        
        assert info.name == "supplier"
        assert info.version == "1.0.0"
        assert info.provides_api is True
        assert info.provides_ui is True
        assert "supplier.created" in info.provides_events
    
    def test_module_initialization(self):
        """测试模块初始化"""
        module = SupplierModule()
        
        # Mock 数据库会话
        mock_db = Mock()
        context = {"database": mock_db, "config": {}}
        
        # 初始化
        result = module.initialize(context)
        
        assert result is True
        assert module.status == ModuleStatus.INITIALIZED
        assert module.supplier_crud is not None
        assert module.risk_agent is not None
        assert module.import_export is not None
    
    def test_module_lifecycle(self):
        """测试模块生命周期"""
        module = SupplierModule()
        
        # Mock 数据库
        mock_db = Mock()
        context = {"database": mock_db, "config": {}}
        
        # 初始化 → 启动 → 停止
        assert module.initialize(context) is True
        assert module.status == ModuleStatus.INITIALIZED
        
        assert module.start() is True
        assert module.status == ModuleStatus.RUNNING
        
        assert module.stop() is True
        assert module.status == ModuleStatus.STOPPED
    
    def test_api_routes(self):
        """测试API路由"""
        module = SupplierModule()
        routes = module.get_api_routes()
        
        assert len(routes) == 8
        
        # 检查关键路由
        paths = [r["path"] for r in routes]
        assert "/api/v1/suppliers" in paths
        assert "/api/v1/suppliers/{supplier_id}" in paths
        assert "/api/v1/suppliers/{supplier_id}/risk" in paths
    
    def test_ui_components(self):
        """测试UI组件"""
        module = SupplierModule()
        components = module.get_ui_components()
        
        assert len(components) == 3
        
        # 检查组件名称
        names = [c["name"] for c in components]
        assert "SupplierList" in names
        assert "SupplierDetail" in names
        assert "SupplierRiskDashboard" in names
    
    def test_health_check(self):
        """测试健康检查"""
        module = SupplierModule()
        
        # Mock 初始化
        module.supplier_crud = Mock()
        module.supplier_crud.count_suppliers.return_value = 10
        module._config = {"enable_risk_assessment": True, "enable_auto_collection": True}
        
        health = module.health_check()
        
        assert health["status"] == "healthy"
        assert health["details"]["supplier_count"] == 10
