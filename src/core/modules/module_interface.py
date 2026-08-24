"""
模块接口定义

所有模块必须实现的标准接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class ModuleStatus(str, Enum):
    """模块状态"""
    UNINITIALIZED = "uninitialized"  # 未初始化
    INITIALIZING = "initializing"    # 初始化中
    INITIALIZED = "initialized"      # 已初始化
    STARTING = "starting"            # 启动中
    RUNNING = "running"              # 运行中
    STOPPING = "stopping"            # 停止中
    STOPPED = "stopped"              # 已停止
    ERROR = "error"                  # 错误状态
    DISABLED = "disabled"            # 已禁用


@dataclass
class ModuleInfo:
    """模块信息"""
    
    # 基本信息
    name: str                           # 模块名称
    version: str                        # 版本号
    description: str                    # 描述
    author: str                         # 作者
    
    # 依赖关系
    dependencies: List[str] = field(default_factory=list)  # 依赖的模块列表
    
    # 模块类型
    is_builtin: bool = True            # 是否内置模块
    is_custom: bool = False            # 是否自定义模块
    
    # 能力声明
    provides_api: bool = False         # 是否提供API
    provides_ui: bool = False          # 是否提供UI组件
    provides_events: List[str] = field(default_factory=list)  # 发布的事件类型
    consumes_events: List[str] = field(default_factory=list)  # 监听的事件类型
    
    # 配置
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置Schema
    default_config: Dict[str, Any] = field(default_factory=dict)  # 默认配置
    
    # 元数据
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 状态
    status: ModuleStatus = ModuleStatus.UNINITIALIZED
    error_message: Optional[str] = None


class ModuleInterface(ABC):
    """
    模块标准接口
    
    所有模块都必须实现这个接口
    """
    
    @abstractmethod
    def get_module_info(self) -> ModuleInfo:
        """
        获取模块信息
        
        Returns:
            ModuleInfo: 模块信息对象
        """
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        初始化模块
        
        Args:
            context: 系统上下文（包含数据库连接、配置等）
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动模块
        
        Returns:
            bool: 启动是否成功
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        停止模块
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """
        获取模块的API路由
        
        Returns:
            List[Dict]: 路由配置列表
            [
                {
                    "path": "/api/v1/module/action",
                    "method": "GET",
                    "handler": handler_function,
                    "tags": ["module"],
                    "summary": "Action description"
                }
            ]
        """
        return []
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """
        获取模块的前端UI组件
        
        Returns:
            List[Dict]: UI组件配置列表
            [
                {
                    "name": "ComponentName",
                    "path": "/dashboard/module",
                    "component": "ModuleComponent",
                    "menu_label": "Module",
                    "icon": "module-icon"
                }
            ]
        """
        return []
    
    def handle_event(self, event: "Event") -> None:
        """
        处理系统事件
        
        Args:
            event: 事件对象
        """
        pass
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取模块当前配置
        
        Returns:
            Dict: 配置字典
        """
        return {}
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """
        更新模块配置
        
        Args:
            config: 新配置
            
        Returns:
            bool: 更新是否成功
        """
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态
            {
                "status": "healthy|degraded|unhealthy",
                "message": "...",
                "details": {...}
            }
        """
        return {
            "status": "healthy",
            "message": "Module is running normally"
        }


class BaseModule(ModuleInterface):
    """
    模块基类
    
    提供常用功能的默认实现
    """
    
    def __init__(self):
        self._status = ModuleStatus.UNINITIALIZED
        self._context = {}
        self._config = {}
        self._error_message = None
    
    @property
    def status(self) -> ModuleStatus:
        """获取模块状态"""
        return self._status
    
    @status.setter
    def status(self, value: ModuleStatus):
        """设置模块状态"""
        self._status = value
        # 更新模块信息中的状态
        info = self.get_module_info()
        info.status = value
    
    @property
    def context(self) -> Dict[str, Any]:
        """获取系统上下文"""
        return self._context
    
    @property
    def config(self) -> Dict[str, Any]:
        """获取模块配置"""
        return self._config
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """初始化模块（默认实现）"""
        try:
            self._status = ModuleStatus.INITIALIZING
            self._context = context
            
            # 加载默认配置
            info = self.get_module_info()
            self._config = info.default_config.copy()
            
            # 子类可以重写 _on_initialize 方法
            result = self._on_initialize()
            
            if result:
                self._status = ModuleStatus.INITIALIZED
            else:
                self._status = ModuleStatus.ERROR
                self._error_message = "Initialization failed"
            
            return result
            
        except Exception as e:
            self._status = ModuleStatus.ERROR
            self._error_message = str(e)
            return False
    
    def start(self) -> bool:
        """启动模块（默认实现）"""
        try:
            self._status = ModuleStatus.STARTING
            
            # 子类可以重写 _on_start 方法
            result = self._on_start()
            
            if result:
                self._status = ModuleStatus.RUNNING
            else:
                self._status = ModuleStatus.ERROR
                self._error_message = "Start failed"
            
            return result
            
        except Exception as e:
            self._status = ModuleStatus.ERROR
            self._error_message = str(e)
            return False
    
    def stop(self) -> bool:
        """停止模块（默认实现）"""
        try:
            self._status = ModuleStatus.STOPPING
            
            # 子类可以重写 _on_stop 方法
            result = self._on_stop()
            
            if result:
                self._status = ModuleStatus.STOPPED
            else:
                self._status = ModuleStatus.ERROR
                self._error_message = "Stop failed"
            
            return result
            
        except Exception as e:
            self._status = ModuleStatus.ERROR
            self._error_message = str(e)
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """获取模块配置"""
        return self._config.copy()
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新模块配置"""
        try:
            self._config.update(config)
            return True
        except Exception:
            return False
    
    # 子类可以重写这些方法
    
    def _on_initialize(self) -> bool:
        """初始化时调用（子类重写）"""
        return True
    
    def _on_start(self) -> bool:
        """启动时调用（子类重写）"""
        return True
    
    def _on_stop(self) -> bool:
        """停止时调用（子类重写）"""
        return True
