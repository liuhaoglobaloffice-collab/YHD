"""
模块化系统测试
"""

import pytest
from src.core.modules import (
    ModuleRegistry,
    ModuleLoader,
    EventBus,
    Event,
    EventType,
    ModuleStatus
)


class TestModuleRegistry:
    """测试模块注册表"""
    
    def test_registry_singleton(self):
        """测试单例模式"""
        registry1 = ModuleRegistry()
        registry2 = ModuleRegistry()
        assert registry1 is registry2
    
    def test_register_module(self):
        """测试注册模块"""
        registry = ModuleRegistry()
        loader = ModuleLoader(registry)
        
        # 加载示例模块
        module = loader.load_module_from_package(
            "src.modules.examples.hello_world_module",
            "HelloWorldModule"
        )
        
        assert module is not None
        
        # 注册模块
        result = registry.register(module)
        assert result is True
        
        # 验证已注册
        info = registry.get_module_info("hello_world")
        assert info is not None
        assert info.name == "hello_world"
        assert info.version == "1.0.0"
    
    def test_enable_disable_module(self):
        """测试启用/禁用模块"""
        registry = ModuleRegistry()
        loader = ModuleLoader(registry)
        
        # 加载并注册模块
        loader.load_and_register(
            "src.modules.examples.hello_world_module",
            auto_enable=False
        )
        
        # 启用模块
        result = registry.enable_module("hello_world")
        assert result is True
        assert registry.is_enabled("hello_world") is True
        
        # 禁用模块
        result = registry.disable_module("hello_world")
        assert result is True
        assert registry.is_enabled("hello_world") is False
    
    def test_module_dependencies(self):
        """测试模块依赖关系"""
        registry = ModuleRegistry()
        
        # 这里可以创建有依赖关系的测试模块
        # 验证拓扑排序等功能
        pass


class TestEventBus:
    """测试事件总线"""
    
    def test_eventbus_singleton(self):
        """测试单例模式"""
        bus1 = EventBus()
        bus2 = EventBus()
        assert bus1 is bus2
    
    def test_subscribe_and_publish(self):
        """测试订阅和发布事件"""
        bus = EventBus()
        bus.reset()  # 清空之前的订阅
        
        # 订阅事件
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
        
        bus.subscribe(EventType.SYSTEM_STARTUP, handler)
        
        # 发布事件
        event = Event(
            type=EventType.SYSTEM_STARTUP,
            source="test",
            data={"message": "test"}
        )
        
        count = bus.publish(event)
        
        assert count == 1
        assert len(received_events) == 1
        assert received_events[0].type == EventType.SYSTEM_STARTUP
    
    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()
        bus.reset()
        
        received_count = [0]
        
        def handler(event: Event):
            received_count[0] += 1
        
        # 订阅
        bus.subscribe(EventType.SYSTEM_STARTUP, handler)
        
        # 发布事件1
        event1 = Event(type=EventType.SYSTEM_STARTUP, source="test")
        bus.publish(event1)
        assert received_count[0] == 1
        
        # 取消订阅
        bus.unsubscribe(EventType.SYSTEM_STARTUP, handler)
        
        # 发布事件2
        event2 = Event(type=EventType.SYSTEM_STARTUP, source="test")
        bus.publish(event2)
        assert received_count[0] == 1  # 不应该再增加
    
    def test_event_history(self):
        """测试事件历史"""
        bus = EventBus()
        bus.clear_history()
        
        # 发布多个事件
        for i in range(5):
            event = Event(
                type=EventType.CUSTOM,
                source="test",
                data={"index": i}
            )
            bus.publish(event)
        
        # 获取历史
        history = bus.get_history(limit=10)
        assert len(history) == 5
        
        # 验证顺序（最新的在前）
        assert history[0].data["index"] == 4
        assert history[4].data["index"] == 0


class TestModuleLoader:
    """测试模块加载器"""
    
    def setup_method(self):
        """每个测试方法执行前重置 Registry"""
        registry = ModuleRegistry()
        registry._reset_for_testing()
    
    def test_load_module_from_package(self):
        """测试从包加载模块"""
        loader = ModuleLoader()
        
        module = loader.load_module_from_package(
            "src.modules.examples.hello_world_module",
            "HelloWorldModule"
        )
        
        assert module is not None
        
        info = module.get_module_info()
        assert info.name == "hello_world"
        assert info.version == "1.0.0"
    
    def test_initialize_module(self):
        """测试初始化模块"""
        loader = ModuleLoader()
        
        # 加载模块
        module = loader.load_module_from_package(
            "src.modules.examples.hello_world_module",
            "HelloWorldModule"
        )
        
        # 注册模块
        loader.registry.register(module)
        loader.registry.enable_module("hello_world")
        
        # 初始化模块
        context = {
            "database": None,
            "config": {}
        }
        
        count = loader.initialize_all_modules(context)
        assert count == 1
        
        # 验证状态
        info = loader.registry.get_module_info("hello_world")
        assert info.status == ModuleStatus.INITIALIZED
    
    def test_start_stop_module(self):
        """测试启动和停止模块"""
        loader = ModuleLoader()
        
        # 加载并初始化模块
        loader.load_and_register(
            "src.modules.examples.hello_world_module",
            auto_enable=True
        )
        
        context = {"database": None, "config": {}}
        loader.initialize_all_modules(context)
        
        # 启动模块
        count = loader.start_all_modules()
        assert count == 1
        
        info = loader.registry.get_module_info("hello_world")
        assert info.status == ModuleStatus.RUNNING
        
        # 停止模块
        count = loader.stop_all_modules()
        assert count == 1
        
        info = loader.registry.get_module_info("hello_world")
        assert info.status == ModuleStatus.STOPPED


class TestHelloWorldModule:
    """测试 Hello World 示例模块"""
    
    def test_module_functionality(self):
        """测试模块功能"""
        loader = ModuleLoader()
        
        # 加载模块
        module = loader.load_module_from_package(
            "src.modules.examples.hello_world_module",
            "HelloWorldModule"
        )
        
        # 初始化并启动
        context = {"database": None, "config": {}}
        module.initialize(context)
        module.start()
        
        # 测试API处理函数
        result = module.handle_hello("Test")
        assert "message" in result
        assert "Test" in result["message"]
        assert result["call_count"] == 1
        
        # 再次调用
        result = module.handle_hello()
        assert result["call_count"] == 2
        
        # 测试统计
        stats = module.handle_stats()
        assert stats["call_count"] == 2
        assert stats["status"] == ModuleStatus.RUNNING.value
        
        # 停止模块
        module.stop()
        assert module.status == ModuleStatus.STOPPED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
