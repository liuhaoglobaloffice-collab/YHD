"""
模块注册表

管理所有已注册的模块
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from .module_interface import ModuleInterface, ModuleInfo, ModuleStatus

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    模块注册表
    
    单例模式，管理系统中所有模块的注册、查询、启用/禁用
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._modules: Dict[str, ModuleInterface] = {}  # 模块实例
        self._module_info: Dict[str, ModuleInfo] = {}   # 模块信息
        self._dependencies: Dict[str, Set[str]] = defaultdict(set)  # 依赖关系图
        self._enabled_modules: Set[str] = set()  # 已启用的模块
        self._initialization_order: List[str] = []  # 初始化顺序（拓扑排序）
        
        self._initialized = True
        logger.info("ModuleRegistry initialized")
    
    def register(self, module: ModuleInterface) -> bool:
        """
        注册模块
        
        Args:
            module: 模块实例
            
        Returns:
            bool: 注册是否成功
        """
        try:
            info = module.get_module_info()
            module_name = info.name
            
            # 检查是否已注册
            if module_name in self._modules:
                logger.warning(f"Module '{module_name}' already registered")
                return False
            
            # 注册模块
            self._modules[module_name] = module
            self._module_info[module_name] = info
            
            # 记录依赖关系
            for dep in info.dependencies:
                self._dependencies[module_name].add(dep)
            
            logger.info(f"Module '{module_name}' registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register module: {e}")
            return False
    
    def unregister(self, module_name: str) -> bool:
        """
        注销模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if module_name not in self._modules:
                logger.warning(f"Module '{module_name}' not found")
                return False
            
            # 检查是否有其他模块依赖它
            dependents = self._get_dependents(module_name)
            if dependents:
                logger.error(
                    f"Cannot unregister '{module_name}': "
                    f"Modules {dependents} depend on it"
                )
                return False
            
            # 如果模块正在运行，先停止
            module = self._modules[module_name]
            if module.get_module_info().status == ModuleStatus.RUNNING:
                module.stop()
            
            # 注销模块
            del self._modules[module_name]
            del self._module_info[module_name]
            
            if module_name in self._dependencies:
                del self._dependencies[module_name]
            
            self._enabled_modules.discard(module_name)
            
            if module_name in self._initialization_order:
                self._initialization_order.remove(module_name)
            
            logger.info(f"Module '{module_name}' unregistered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister module '{module_name}': {e}")
            return False
    
    def get_module(self, module_name: str) -> Optional[ModuleInterface]:
        """
        获取模块实例
        
        Args:
            module_name: 模块名称
            
        Returns:
            ModuleInterface: 模块实例，如果不存在返回None
        """
        return self._modules.get(module_name)
    
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """
        获取模块信息
        
        Args:
            module_name: 模块名称
            
        Returns:
            ModuleInfo: 模块信息，如果不存在返回None
        """
        # 从模块实例获取最新信息（包含最新状态）
        module = self._modules.get(module_name)
        if module:
            info = module.get_module_info()
            # 更新状态
            info.status = module.status
            return info
        return None
    
    def list_modules(self, 
                     status: Optional[ModuleStatus] = None,
                     enabled_only: bool = False) -> List[ModuleInfo]:
        """
        列出所有模块
        
        Args:
            status: 筛选特定状态的模块
            enabled_only: 只列出已启用的模块
            
        Returns:
            List[ModuleInfo]: 模块信息列表
        """
        modules = []
        
        for name in self._modules.keys():
            # 从模块实例获取最新信息
            info = self.get_module_info(name)
            if info is None:
                continue
            
            # 筛选条件
            if status and info.status != status:
                continue
            if enabled_only and name not in self._enabled_modules:
                continue
            
            modules.append(info)
        
        return modules
    
    def enable_module(self, module_name: str) -> bool:
        """
        启用模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否成功
        """
        if module_name not in self._modules:
            logger.error(f"Module '{module_name}' not found")
            return False
        
        self._enabled_modules.add(module_name)
        logger.info(f"Module '{module_name}' enabled")
        return True
    
    def disable_module(self, module_name: str) -> bool:
        """
        禁用模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否成功
        """
        if module_name not in self._modules:
            logger.error(f"Module '{module_name}' not found")
            return False
        
        # 检查是否有依赖它的已启用模块
        dependents = [
            dep for dep in self._get_dependents(module_name)
            if dep in self._enabled_modules
        ]
        
        if dependents:
            logger.error(
                f"Cannot disable '{module_name}': "
                f"Enabled modules {dependents} depend on it"
            )
            return False
        
        # 如果模块正在运行，先停止
        module = self._modules[module_name]
        if module.get_module_info().status == ModuleStatus.RUNNING:
            module.stop()
        
        self._enabled_modules.discard(module_name)
        logger.info(f"Module '{module_name}' disabled")
        return True
    
    def is_enabled(self, module_name: str) -> bool:
        """检查模块是否已启用"""
        return module_name in self._enabled_modules
    
    def compute_initialization_order(self) -> List[str]:
        """
        计算模块初始化顺序（拓扑排序）
        
        Returns:
            List[str]: 模块名称列表（按初始化顺序）
        """
        # Kahn算法（拓扑排序）
        in_degree = defaultdict(int)
        graph = defaultdict(set)
        
        # 只考虑已启用的模块
        enabled_modules = self._enabled_modules.copy()
        
        # 构建图和入度
        for module_name in enabled_modules:
            for dep in self._dependencies[module_name]:
                if dep in enabled_modules:
                    graph[dep].add(module_name)
                    in_degree[module_name] += 1
        
        # 找出所有入度为0的节点
        queue = [m for m in enabled_modules if in_degree[m] == 0]
        result = []
        
        while queue:
            # 取出一个入度为0的节点
            node = queue.pop(0)
            result.append(node)
            
            # 将该节点的所有出边删除
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(result) != len(enabled_modules):
            missing = enabled_modules - set(result)
            logger.error(f"Circular dependency detected: {missing}")
            raise ValueError(f"Circular dependency detected: {missing}")
        
        self._initialization_order = result
        return result
    
    def get_initialization_order(self) -> List[str]:
        """获取模块初始化顺序"""
        if not self._initialization_order:
            self.compute_initialization_order()
        return self._initialization_order
    
    def _get_dependents(self, module_name: str) -> Set[str]:
        """
        获取依赖指定模块的所有模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            Set[str]: 依赖该模块的模块名称集合
        """
        dependents = set()
        for name, deps in self._dependencies.items():
            if module_name in deps:
                dependents.add(name)
        return dependents
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取注册表统计信息
        
        Returns:
            Dict: 统计信息
        """
        status_count = defaultdict(int)
        for info in self._module_info.values():
            status_count[info.status.value] += 1
        
        return {
            "total_modules": len(self._modules),
            "enabled_modules": len(self._enabled_modules),
            "disabled_modules": len(self._modules) - len(self._enabled_modules),
            "status_breakdown": dict(status_count),
            "builtin_modules": sum(1 for info in self._module_info.values() if info.is_builtin),
            "custom_modules": sum(1 for info in self._module_info.values() if info.is_custom),
        }
    
    def _reset_for_testing(self):
        """
        重置注册表（仅用于测试）
        
        Warning:
            此方法仅用于测试，不应在生产代码中使用！
        """
        self._modules.clear()
        self._module_info.clear()
        self._enabled_modules.clear()
        self._dependencies.clear()
        self._initialization_order.clear()
        logger.warning("注意：ModuleRegistry 已重置（仅用于测试）")
