"""
模块加载器

动态加载和卸载模块
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

from .module_interface import ModuleInterface, ModuleInfo, ModuleStatus
from .module_registry import ModuleRegistry
from .event_bus import EventBus, Event, EventType

logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    模块加载器
    
    负责动态加载和卸载模块
    """
    
    def __init__(self, registry: Optional[ModuleRegistry] = None):
        self.registry = registry or ModuleRegistry()
        self.event_bus = EventBus()
        self._loaded_modules: Dict[str, str] = {}  # module_name -> module_path
    
    def load_module_from_path(self, 
                              module_path: str, 
                              module_name: Optional[str] = None) -> Optional[ModuleInterface]:
        """
        从文件路径加载模块
        
        Args:
            module_path: 模块文件路径
            module_name: 模块名称（可选，自动从路径推断）
            
        Returns:
            ModuleInterface: 加载的模块实例，失败返回None
        """
        try:
            path = Path(module_path)
            
            if not path.exists():
                logger.error(f"Module file not found: {module_path}")
                return None
            
            # 推断模块名称
            if not module_name:
                module_name = path.stem
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for: {module_path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找实现了 ModuleInterface 的类
            module_instance = self._find_module_class(module)
            
            if module_instance is None:
                logger.error(f"No ModuleInterface implementation found in: {module_path}")
                return None
            
            # 记录加载路径
            self._loaded_modules[module_instance.get_module_info().name] = module_path
            
            logger.info(f"Module loaded from: {module_path}")
            return module_instance
            
        except Exception as e:
            logger.error(f"Failed to load module from {module_path}: {e}", exc_info=True)
            return None
    
    def load_module_from_package(self, 
                                 package_name: str, 
                                 class_name: Optional[str] = None) -> Optional[ModuleInterface]:
        """
        从Python包加载模块
        
        Args:
            package_name: 包名（如 "src.modules.my_module"）
            class_name: 模块类名（可选）
            
        Returns:
            ModuleInterface: 加载的模块实例，失败返回None
        """
        try:
            # 导入包
            module = importlib.import_module(package_name)
            
            # 如果指定了类名，直接实例化
            if class_name:
                module_class = getattr(module, class_name, None)
                if module_class is None:
                    logger.error(f"Class '{class_name}' not found in package '{package_name}'")
                    return None
                
                module_instance = module_class()
            else:
                # 查找实现了 ModuleInterface 的类
                module_instance = self._find_module_class(module)
            
            if module_instance is None:
                logger.error(f"No ModuleInterface implementation found in package: {package_name}")
                return None
            
            # 记录加载路径
            self._loaded_modules[module_instance.get_module_info().name] = package_name
            
            logger.info(f"Module loaded from package: {package_name}")
            return module_instance
            
        except Exception as e:
            logger.error(f"Failed to load module from package {package_name}: {e}", exc_info=True)
            return None
    
    def load_and_register(self, 
                          module_path: str, 
                          auto_enable: bool = True) -> bool:
        """
        加载并注册模块
        
        Args:
            module_path: 模块路径（文件路径或包名）
            auto_enable: 是否自动启用
            
        Returns:
            bool: 是否成功
        """
        try:
            # 判断是文件路径还是包名
            if Path(module_path).exists():
                module_instance = self.load_module_from_path(module_path)
            else:
                module_instance = self.load_module_from_package(module_path)
            
            if module_instance is None:
                return False
            
            # 注册模块
            if not self.registry.register(module_instance):
                return False
            
            # 发布模块注册事件
            event = Event(
                type=EventType.MODULE_REGISTERED,
                source="module_loader",
                data={
                    "module_name": module_instance.get_module_info().name,
                    "module_path": module_path
                }
            )
            self.event_bus.publish(event)
            
            # 自动启用
            if auto_enable:
                self.registry.enable_module(module_instance.get_module_info().name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load and register module from {module_path}: {e}")
            return False
    
    def unload_module(self, module_name: str) -> bool:
        """
        卸载模块
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否成功
        """
        try:
            # 从注册表注销
            if not self.registry.unregister(module_name):
                return False
            
            # 从已加载模块中移除
            if module_name in self._loaded_modules:
                del self._loaded_modules[module_name]
            
            # 从sys.modules中移除（可选，谨慎操作）
            # if module_name in sys.modules:
            #     del sys.modules[module_name]
            
            # 发布模块注销事件
            event = Event(
                type=EventType.MODULE_UNREGISTERED,
                source="module_loader",
                data={"module_name": module_name}
            )
            self.event_bus.publish(event)
            
            logger.info(f"Module '{module_name}' unloaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload module '{module_name}': {e}")
            return False
    
    def reload_module(self, module_name: str) -> bool:
        """
        重新加载模块（热更新）
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取模块路径
            if module_name not in self._loaded_modules:
                logger.error(f"Module '{module_name}' not found in loaded modules")
                return False
            
            module_path = self._loaded_modules[module_name]
            
            # 卸载模块
            if not self.unload_module(module_name):
                return False
            
            # 重新加载
            if not self.load_and_register(module_path):
                return False
            
            logger.info(f"Module '{module_name}' reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload module '{module_name}': {e}")
            return False
    
    def load_modules_from_directory(self, 
                                     directory: str, 
                                     auto_enable: bool = True,
                                     recursive: bool = False) -> int:
        """
        从目录加载所有模块
        
        Args:
            directory: 目录路径
            auto_enable: 是否自动启用
            recursive: 是否递归子目录
            
        Returns:
            int: 成功加载的模块数量
        """
        try:
            dir_path = Path(directory)
            
            if not dir_path.exists() or not dir_path.is_dir():
                logger.error(f"Directory not found: {directory}")
                return 0
            
            # 查找所有Python文件
            if recursive:
                pattern = "**/*.py"
            else:
                pattern = "*.py"
            
            python_files = list(dir_path.glob(pattern))
            
            # 排除 __init__.py
            python_files = [f for f in python_files if f.name != "__init__.py"]
            
            # 加载模块
            success_count = 0
            for file_path in python_files:
                if self.load_and_register(str(file_path), auto_enable):
                    success_count += 1
            
            logger.info(
                f"Loaded {success_count}/{len(python_files)} modules from {directory}"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to load modules from directory {directory}: {e}")
            return 0
    
    def initialize_all_modules(self, context: Dict[str, Any]) -> int:
        """
        初始化所有已启用的模块
        
        Args:
            context: 系统上下文
            
        Returns:
            int: 成功初始化的模块数量
        """
        try:
            # 计算初始化顺序（考虑依赖关系）
            init_order = self.registry.compute_initialization_order()
            
            success_count = 0
            for module_name in init_order:
                module = self.registry.get_module(module_name)
                if module is None:
                    continue
                
                logger.info(f"Initializing module '{module_name}'...")
                
                if module.initialize(context):
                    success_count += 1
                    logger.info(f"Module '{module_name}' initialized successfully")
                else:
                    logger.error(f"Failed to initialize module '{module_name}'")
            
            logger.info(
                f"Initialized {success_count}/{len(init_order)} modules"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to initialize modules: {e}")
            return 0
    
    def start_all_modules(self) -> int:
        """
        启动所有已初始化的模块
        
        Returns:
            int: 成功启动的模块数量
        """
        try:
            # 获取所有已初始化的模块
            modules = self.registry.list_modules(
                status=ModuleStatus.INITIALIZED,
                enabled_only=True
            )
            
            success_count = 0
            for module_info in modules:
                module = self.registry.get_module(module_info.name)
                if module is None:
                    continue
                
                logger.info(f"Starting module '{module_info.name}'...")
                
                if module.start():
                    success_count += 1
                    
                    # 发布模块启动事件
                    event = Event(
                        type=EventType.MODULE_STARTED,
                        source="module_loader",
                        data={"module_name": module_info.name}
                    )
                    self.event_bus.publish(event)
                    
                    logger.info(f"Module '{module_info.name}' started successfully")
                else:
                    logger.error(f"Failed to start module '{module_info.name}'")
            
            logger.info(
                f"Started {success_count}/{len(modules)} modules"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to start modules: {e}")
            return 0
    
    def stop_all_modules(self) -> int:
        """
        停止所有运行中的模块
        
        Returns:
            int: 成功停止的模块数量
        """
        try:
            # 获取所有运行中的模块
            modules = self.registry.list_modules(
                status=ModuleStatus.RUNNING,
                enabled_only=False  # 停止所有运行中的模块，包括已禁用的
            )
            
            # 直接停止所有运行中的模块
            success_count = 0
            for module_info in modules:
                module = self.registry.get_module(module_info.name)
                if module is None:
                    continue
                
                logger.info(f"Stopping module '{module_info.name}'...")
                
                if module.stop():
                    success_count += 1
                    
                    # 发布模块停止事件
                    event = Event(
                        type=EventType.MODULE_STOPPED,
                        source="module_loader",
                        data={"module_name": module_info.name}
                    )
                    self.event_bus.publish(event)
                    
                    logger.info(f"Module '{module_info.name}' stopped successfully")
                else:
                    logger.error(f"Failed to stop module '{module_info.name}'")
            
            logger.info(
                f"Stopped {success_count}/{len(modules)} modules"
            )
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to stop modules: {e}")
            return 0
    
    def _find_module_class(self, module) -> Optional[ModuleInterface]:
        """
        在模块中查找实现了 ModuleInterface 的类
        
        Args:
            module: 已加载的Python模块
            
        Returns:
            ModuleInterface: 模块实例，如果没找到返回None
        """
        try:
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # 检查是否是类
                if not isinstance(attr, type):
                    continue
                
                # 检查是否实现了 ModuleInterface（排除ModuleInterface和BaseModule）
                if (issubclass(attr, ModuleInterface) and 
                    attr is not ModuleInterface and 
                    attr.__name__ != 'BaseModule'):
                    # 实例化
                    return attr()
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding module class: {e}")
            return None
    
    def get_loaded_modules(self) -> List[str]:
        """获取所有已加载的模块名称"""
        return list(self._loaded_modules.keys())
