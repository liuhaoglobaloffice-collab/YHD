"""
测试 AI 专家管理模块
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.modules.ai_expert_module import (
    AIExpertModule,
    ExpertType,
    ExpertStatus,
    AIExpertConfig
)
from src.core.modules import ModuleStatus


class TestAIExpertModule:
    """测试 AI 专家管理模块"""
    
    def setup_method(self):
        """每个测试方法前重置模块注册表"""
        from src.core.modules import ModuleRegistry
        registry = ModuleRegistry()
        registry._modules = {}
    
    def test_module_info(self):
        """测试模块信息"""
        module = AIExpertModule()
        info = module.get_module_info()
        
        assert info.name == "ai_expert"
        assert info.version == "1.0.0"
        assert info.provides_api is True
        assert info.provides_ui is True
        assert "expert.created" in info.provides_events
        assert "expert.updated" in info.provides_events
        assert "expert.deleted" in info.provides_events
        assert "expert.tested" in info.provides_events
        assert "expert.status_changed" in info.provides_events
    
    def test_core_experts_preloaded(self):
        """测试10个核心专家是否预加载"""
        module = AIExpertModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        # 初始化
        context = {"config": {}}
        module.initialize(context)
        
        # 验证10个核心专家
        assert len(module.experts) == 10
        
        # 验证核心专家类型（注意：属性名是 type 不是 expert_type）
        expert_types = [e.type for e in module.experts.values()]
        assert ExpertType.DATA_COLLECTOR in expert_types
        assert ExpertType.RISK_ASSESSOR in expert_types
        assert ExpertType.TEXT_GENERATOR in expert_types
        assert ExpertType.DATA_ANALYST in expert_types
        assert ExpertType.TRANSLATOR in expert_types
        assert ExpertType.SUMMARIZER in expert_types
        assert ExpertType.QA_EXPERT in expert_types
        assert ExpertType.CODE_GENERATOR in expert_types
        assert ExpertType.SENTIMENT_ANALYZER in expert_types
        assert ExpertType.ENTITY_RECOGNIZER in expert_types
        
        # 验证所有核心专家标记
        for expert in module.experts.values():
            assert expert.is_custom is False
    
    def test_module_initialization(self):
        """测试模块初始化"""
        module = AIExpertModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        context = {"config": {"max_experts": 32}}
        
        # 初始化
        result = module.initialize(context)
        
        assert result is True
        assert module.status == ModuleStatus.INITIALIZED
        assert len(module.experts) == 10
        assert module.config.get("max_experts") == 32
    
    def test_module_lifecycle(self):
        """测试模块生命周期"""
        module = AIExpertModule()
        
        # Mock EventBus
        module.event_bus = Mock()
        
        context = {"config": {}}
        
        # 初始化 → 启动 → 停止
        assert module.initialize(context) is True
        assert module.status == ModuleStatus.INITIALIZED
        
        assert module.start() is True
        assert module.status == ModuleStatus.RUNNING
        
        assert module.stop() is True
        assert module.status == ModuleStatus.STOPPED
    
    def test_api_routes(self):
        """测试API路由"""
        module = AIExpertModule()
        routes = module.get_api_routes()
        
        assert len(routes) == 9
        
        # 检查关键路由
        paths = [r["path"] for r in routes]
        assert "/api/v1/experts" in paths
        assert "/api/v1/experts/{expert_id}" in paths
        assert "/api/v1/experts/{expert_id}/test" in paths
        assert "/api/v1/experts/{expert_id}/enable" in paths
        assert "/api/v1/experts/{expert_id}/disable" in paths
        assert "/api/v1/experts/stats" in paths
    
    def test_ui_components(self):
        """测试UI组件"""
        module = AIExpertModule()
        components = module.get_ui_components()
        
        assert len(components) == 4
        
        # 检查组件名称
        names = [c["name"] for c in components]
        assert "ExpertList" in names
        assert "ExpertConfig" in names
        assert "ExpertDashboard" in names
        assert "ExpertCreate" in names
    
    def test_create_custom_expert(self):
        """测试创建自定义专家"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 创建自定义专家
        expert_data = {
            "name": "Custom Expert",
            "type": ExpertType.CUSTOM_11,  # 属性名是 type
            "description": "Test custom expert",
            "api_url": "https://api.example.com",
            "api_key": "test_key",
            "model": "gpt-4"
        }
        
        result = module.create_expert(expert_data)
        
        assert "data" in result
        expert_id = result["data"]["id"]
        # 从模块获取专家对象
        expert = module.experts[expert_id]
        assert expert.name == "Custom Expert"
        assert expert.is_custom is True
        assert expert.type == ExpertType.CUSTOM_11
        assert len(module.experts) == 11
    
    def test_update_expert(self):
        """测试更新专家"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 获取第一个专家
        expert_id = list(module.experts.keys())[0]
        
        # 更新
        update_data = {
            "api_url": "https://new-api.example.com",
            "api_key": "new_key"
        }
        
        result = module.update_expert(expert_id, update_data)
        
        assert "data" in result
        # 从模块获取更新后的专家
        expert = module.experts[expert_id]
        assert expert.api_url == "https://new-api.example.com"
        assert expert.api_key == "new_key"
    
    def test_cannot_delete_core_expert(self):
        """测试核心专家不可删除"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 尝试删除核心专家
        core_expert_id = list(module.experts.keys())[0]
        
        result = module.delete_expert(core_expert_id)
        
        assert "error" in result
        assert "Cannot delete core expert" in result["error"]
        assert len(module.experts) == 10  # 数量不变
    
    def test_can_delete_custom_expert(self):
        """测试可以删除自定义专家"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        # 创建自定义专家
        expert_data = {
            "name": "Custom Expert",
            "type": ExpertType.CUSTOM_11,
            "description": "Test",
            "api_url": "https://api.example.com"  # 必填字段
        }
        
        create_result = module.create_expert(expert_data)
        custom_expert_id = create_result["data"]["id"]
        
        # 删除自定义专家
        result = module.delete_expert(custom_expert_id)
        
        assert "success" in result
        assert result["success"] is True
        assert len(module.experts) == 10  # 回到原始数量
    
    def test_max_experts_limit(self):
        """测试32个专家上限"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {"max_experts": 32}}
        module.initialize(context)
        
        # 创建22个自定义专家（10个核心 + 22个自定义 = 32）
        for i in range(22):
            expert_data = {
                "name": f"Custom Expert {i+1}",
                "type": getattr(ExpertType, f"CUSTOM_{i+11}"),
                "description": f"Test expert {i+1}",
                "api_url": f"https://api-{i+11}.example.com"  # 必填字段
            }
            module.create_expert(expert_data)
        
        assert len(module.experts) == 32
        
        # 尝试创建第33个专家
        extra_expert = {
            "name": "Extra Expert",
            "type": ExpertType.CUSTOM_11,
            "description": "Should fail",
            "api_url": "https://api.example.com"
        }
        
        result = module.create_expert(extra_expert)
        
        assert "error" in result
        assert "Maximum" in result["error"]
    
    def test_expert_test_connection(self):
        """测试专家连接测试"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        expert_id = list(module.experts.keys())[0]
        
        # 测试连接
        result = module.test_expert(expert_id)
        
        assert "data" in result
        assert result["data"]["success"] is True
        assert "response_time" in result["data"]
    
    def test_enable_disable_expert(self):
        """测试启用/禁用专家"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        expert_id = list(module.experts.keys())[0]
        expert = module.experts[expert_id]
        
        # 初始状态应该是启用的
        assert expert.enabled is True
        
        # 禁用
        result = module.disable_expert(expert_id)
        assert result["success"] is True
        assert expert.enabled is False
        
        # 启用
        result = module.enable_expert(expert_id)
        assert result["success"] is True
        assert expert.enabled is True
    
    def test_get_stats(self):
        """测试统计信息"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {"max_experts": 32}}
        module.initialize(context)
        
        # 添加2个自定义专家
        for i in range(2):
            expert_data = {
                "name": f"Custom {i+1}",
                "type": getattr(ExpertType, f"CUSTOM_{i+11}"),
                "description": "Test",
                "api_url": f"https://api-{i+11}.example.com"
            }
            module.create_expert(expert_data)
        
        result = module.get_stats()
        stats = result["data"]
        
        assert stats["total"] == 12
        assert stats["core"] == 10
        assert stats["custom"] == 2
        assert stats["max_allowed"] == 32
        assert stats["available_slots"] == 20
    
    def test_health_check(self):
        """测试健康检查"""
        module = AIExpertModule()
        module.event_bus = Mock()
        
        context = {"config": {}}
        module.initialize(context)
        
        health = module.health_check()
        
        assert health["status"] == "healthy"
        assert "message" in health
        assert "details" in health
        assert health["details"]["total"] == 10
