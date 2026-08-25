"""
模块化系统核心组件

提供模块注册、加载、管理功能
"""

from .module_interface import ModuleInterface, ModuleInfo, ModuleStatus, BaseModule
from .module_registry import ModuleRegistry
from .module_loader import ModuleLoader
from .event_bus import EventBus, Event, EventType

__all__ = [
    "ModuleInterface",
    "ModuleInfo",
    "ModuleStatus",
    "BaseModule",
    "ModuleRegistry",
    "ModuleLoader",
    "EventBus",
    "Event",
    "EventType",
]
