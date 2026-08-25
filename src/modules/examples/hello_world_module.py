"""
示例模块

演示如何创建一个简单的模块
"""

from src.core.modules import BaseModule, ModuleInfo, EventBus, Event, EventType
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class HelloWorldModule(BaseModule):
    """
    Hello World 示例模块
    
    这是一个最简单的模块示例，展示了：
    1. 如何继承 BaseModule
    2. 如何实现必需的方法
    3. 如何提供API路由
    4. 如何监听和发布事件
    """
    
    def __init__(self):
        super().__init__()
        self.event_bus = EventBus()
        self.call_count = 0
    
    def get_module_info(self) -> ModuleInfo:
        """返回模块信息"""
        return ModuleInfo(
            name="hello_world",
            version="1.0.0",
            description="一个简单的 Hello World 示例模块",
            author="LiuHao AI-OS Team",
            
            # 依赖关系（这个模块不依赖其他模块）
            dependencies=[],
            
            # 模块类型
            is_builtin=False,
            is_custom=True,
            
            # 能力声明
            provides_api=True,
            provides_ui=True,
            provides_events=["hello_world.greeted"],
            consumes_events=["system.startup"],
            
            # 配置Schema
            default_config={
                "greeting": "Hello",
                "name": "World",
                "enabled": True
            }
        )
    
    def _on_initialize(self) -> bool:
        """初始化时调用"""
        logger.info("HelloWorldModule: Initializing...")
        
        # 订阅系统启动事件
        self.event_bus.subscribe(EventType.SYSTEM_STARTUP, self._on_system_startup)
        
        logger.info("HelloWorldModule: Initialized successfully")
        return True
    
    def _on_start(self) -> bool:
        """启动时调用"""
        logger.info("HelloWorldModule: Starting...")
        
        # 可以在这里启动后台任务、连接数据库等
        greeting = self.config.get("greeting", "Hello")
        name = self.config.get("name", "World")
        
        message = f"{greeting}, {name}!"
        logger.info(f"HelloWorldModule: {message}")
        
        logger.info("HelloWorldModule: Started successfully")
        return True
    
    def _on_stop(self) -> bool:
        """停止时调用"""
        logger.info("HelloWorldModule: Stopping...")
        
        # 清理资源
        logger.info(f"HelloWorldModule: Total calls: {self.call_count}")
        
        logger.info("HelloWorldModule: Stopped successfully")
        return True
    
    def _on_system_startup(self, event: Event):
        """监听系统启动事件"""
        logger.info("HelloWorldModule: Received system startup event")
        
        # 发布一个自定义事件
        greeting_event = Event(
            type=EventType.CUSTOM,
            source="hello_world",
            data={
                "event_name": "hello_world.greeted",
                "message": "Hello from HelloWorldModule!",
                "timestamp": event.timestamp
            }
        )
        self.event_bus.publish(greeting_event)
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """返回API路由"""
        return [
            {
                "path": "/api/v1/hello",
                "method": "GET",
                "handler": self.handle_hello,
                "tags": ["hello_world"],
                "summary": "获取问候消息"
            },
            {
                "path": "/api/v1/hello/stats",
                "method": "GET",
                "handler": self.handle_stats,
                "tags": ["hello_world"],
                "summary": "获取调用统计"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """返回UI组件"""
        return [
            {
                "name": "HelloWorldWidget",
                "path": "/dashboard/hello-world",
                "component": "HelloWorldWidget",
                "menu_label": "Hello World",
                "icon": "wave",
                "description": "Hello World 示例模块"
            }
        ]
    
    def handle_hello(self, name: str = None) -> Dict[str, Any]:
        """
        处理 /api/v1/hello 请求
        
        Args:
            name: 名字（可选）
            
        Returns:
            Dict: 响应数据
        """
        self.call_count += 1
        
        greeting = self.config.get("greeting", "Hello")
        target_name = name or self.config.get("name", "World")
        
        return {
            "message": f"{greeting}, {target_name}!",
            "call_count": self.call_count,
            "module": "hello_world",
            "version": "1.0.0"
        }
    
    def handle_stats(self) -> Dict[str, Any]:
        """
        处理 /api/v1/hello/stats 请求
        
        Returns:
            Dict: 统计数据
        """
        return {
            "module": "hello_world",
            "status": self.status.value,
            "call_count": self.call_count,
            "config": self.config
        }
    
    def handle_event(self, event: Event):
        """处理事件"""
        if event.type == EventType.SYSTEM_STARTUP:
            self._on_system_startup(event)
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if self.call_count < 1000 else "degraded",
            "message": f"Module is running, handled {self.call_count} requests",
            "details": {
                "call_count": self.call_count,
                "config": self.config
            }
        }
