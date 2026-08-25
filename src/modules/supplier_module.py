"""
Supplier 模块

整合供应商管理的所有功能:
- 供应商 CRUD
- 数据采集
- 风险评估
- 导入导出
"""

from src.core.modules import BaseModule, ModuleInfo, EventBus, Event, EventType
from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.risk_agent import SupplierRiskAgent
from src.business.supplier.import_export import SupplierImportExport
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SupplierModule(BaseModule):
    """
    供应商管理模块
    
    提供完整的供应商管理功能:
    - CRUD 操作
    - 风险评估
    - 数据导入导出
    - 智能数据采集
    """
    
    def __init__(self):
        super().__init__()
        self.event_bus = EventBus()
        self.supplier_crud = None
        self.risk_agent = None
        self.import_export = None
    
    def get_module_info(self) -> ModuleInfo:
        """返回模块信息"""
        return ModuleInfo(
            name="supplier",
            version="1.0.0",
            description="供应商智能管理模块 - 提供CRUD、风险评估、数据采集功能",
            author="LiuHao AI-OS Team",
            
            # 依赖关系
            dependencies=[],  # 独立模块
            
            # 模块类型
            is_builtin=True,
            is_custom=False,
            
            # 能力声明
            provides_api=True,
            provides_ui=True,
            provides_events=["supplier.created", "supplier.updated", "supplier.deleted", "supplier.risk_assessed"],
            consumes_events=["system.startup"],
            
            # 配置Schema
            default_config={
                "enable_risk_assessment": True,
                "enable_auto_collection": True,
                "risk_threshold": 0.7,
                "auto_update_interval": 3600  # 秒
            }
        )
    
    def _on_initialize(self) -> bool:
        """初始化模块"""
        try:
            logger.info("SupplierModule: Initializing...")
            
            # 获取数据库会话
            db_session = self.context.get("database")
            if not db_session:
                logger.error("SupplierModule: Database session not found in context")
                return False
            
            # 初始化组件
            self.supplier_crud = SupplierCRUD(db_session)
            self.risk_agent = SupplierRiskAgent(db_session)
            self.import_export = SupplierImportExport(db_session)
            
            # 订阅系统事件
            self.event_bus.subscribe(EventType.SYSTEM_STARTUP, self._on_system_startup)
            
            logger.info("SupplierModule: Initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"SupplierModule: Initialization failed: {e}")
            return False
    
    def _on_start(self) -> bool:
        """启动模块"""
        try:
            logger.info("SupplierModule: Starting...")
            
            # 检查配置
            if self.config.get("enable_risk_assessment"):
                logger.info("SupplierModule: Risk assessment enabled")
            
            if self.config.get("enable_auto_collection"):
                logger.info("SupplierModule: Auto data collection enabled")
            
            logger.info("SupplierModule: Started successfully")
            return True
            
        except Exception as e:
            logger.error(f"SupplierModule: Start failed: {e}")
            return False
    
    def _on_stop(self) -> bool:
        """停止模块"""
        try:
            logger.info("SupplierModule: Stopping...")
            
            # 清理资源
            # TODO: 停止后台任务（如果有）
            
            logger.info("SupplierModule: Stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"SupplierModule: Stop failed: {e}")
            return False
    
    def _on_system_startup(self, event: Event):
        """监听系统启动事件"""
        logger.info("SupplierModule: System started, supplier module ready")
        
        # 发布模块就绪事件
        ready_event = Event(
            type=EventType.CUSTOM,
            source="supplier",
            data={
                "event_name": "supplier.module_ready",
                "message": "Supplier module is ready to handle requests"
            }
        )
        self.event_bus.publish(ready_event)
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """返回API路由"""
        return [
            # Supplier CRUD
            {
                "path": "/api/v1/suppliers",
                "method": "GET",
                "handler": self.list_suppliers,
                "tags": ["supplier"],
                "summary": "列出所有供应商"
            },
            {
                "path": "/api/v1/suppliers/{supplier_id}",
                "method": "GET",
                "handler": self.get_supplier,
                "tags": ["supplier"],
                "summary": "获取供应商详情"
            },
            {
                "path": "/api/v1/suppliers",
                "method": "POST",
                "handler": self.create_supplier,
                "tags": ["supplier"],
                "summary": "创建供应商"
            },
            {
                "path": "/api/v1/suppliers/{supplier_id}",
                "method": "PUT",
                "handler": self.update_supplier,
                "tags": ["supplier"],
                "summary": "更新供应商"
            },
            {
                "path": "/api/v1/suppliers/{supplier_id}",
                "method": "DELETE",
                "handler": self.delete_supplier,
                "tags": ["supplier"],
                "summary": "删除供应商"
            },
            
            # Risk Assessment
            {
                "path": "/api/v1/suppliers/{supplier_id}/risk",
                "method": "POST",
                "handler": self.assess_risk,
                "tags": ["supplier", "risk"],
                "summary": "评估供应商风险"
            },
            
            # Import/Export
            {
                "path": "/api/v1/suppliers/import",
                "method": "POST",
                "handler": self.import_suppliers,
                "tags": ["supplier", "import"],
                "summary": "导入供应商数据"
            },
            {
                "path": "/api/v1/suppliers/export",
                "method": "GET",
                "handler": self.export_suppliers,
                "tags": ["supplier", "export"],
                "summary": "导出供应商数据"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """返回UI组件"""
        return [
            {
                "name": "SupplierList",
                "path": "/suppliers",
                "component": "SupplierList",
                "menu_label": "供应商管理",
                "menu_group": "业务管理",
                "icon": "factory",
                "description": "供应商列表与管理"
            },
            {
                "name": "SupplierDetail",
                "path": "/suppliers/:id",
                "component": "SupplierDetail",
                "menu_label": "",  # 不显示在菜单
                "icon": "info-circle",
                "description": "供应商详情页"
            },
            {
                "name": "SupplierRiskDashboard",
                "path": "/suppliers/risk",
                "component": "SupplierRiskDashboard",
                "menu_label": "供应商风险",
                "menu_group": "业务管理",
                "icon": "alert-triangle",
                "description": "供应商风险评估仪表板"
            }
        ]
    
    # API Handler 实现
    
    def list_suppliers(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """列出供应商"""
        try:
            suppliers = self.supplier_crud.list_suppliers(skip=skip, limit=limit)
            total = self.supplier_crud.count_suppliers()
            
            return {
                "data": [s.to_dict() for s in suppliers],
                "total": total,
                "skip": skip,
                "limit": limit
            }
        except Exception as e:
            logger.error(f"SupplierModule: List suppliers failed: {e}")
            return {"error": str(e)}
    
    def get_supplier(self, supplier_id: int) -> Dict[str, Any]:
        """获取供应商详情"""
        try:
            supplier = self.supplier_crud.get_supplier(supplier_id)
            if not supplier:
                return {"error": "Supplier not found"}
            
            return {"data": supplier.to_dict()}
        except Exception as e:
            logger.error(f"SupplierModule: Get supplier failed: {e}")
            return {"error": str(e)}
    
    def create_supplier(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建供应商"""
        try:
            supplier = self.supplier_crud.create_supplier(data)
            
            # 发布创建事件
            event = Event(
                type=EventType.CUSTOM,
                source="supplier",
                data={
                    "event_name": "supplier.created",
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name
                }
            )
            self.event_bus.publish(event)
            
            return {"data": supplier.to_dict()}
        except Exception as e:
            logger.error(f"SupplierModule: Create supplier failed: {e}")
            return {"error": str(e)}
    
    def update_supplier(self, supplier_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新供应商"""
        try:
            supplier = self.supplier_crud.update_supplier(supplier_id, data)
            if not supplier:
                return {"error": "Supplier not found"}
            
            # 发布更新事件
            event = Event(
                type=EventType.CUSTOM,
                source="supplier",
                data={
                    "event_name": "supplier.updated",
                    "supplier_id": supplier.id,
                    "supplier_name": supplier.name
                }
            )
            self.event_bus.publish(event)
            
            return {"data": supplier.to_dict()}
        except Exception as e:
            logger.error(f"SupplierModule: Update supplier failed: {e}")
            return {"error": str(e)}
    
    def delete_supplier(self, supplier_id: int) -> Dict[str, Any]:
        """删除供应商"""
        try:
            success = self.supplier_crud.delete_supplier(supplier_id)
            if not success:
                return {"error": "Supplier not found"}
            
            # 发布删除事件
            event = Event(
                type=EventType.CUSTOM,
                source="supplier",
                data={
                    "event_name": "supplier.deleted",
                    "supplier_id": supplier_id
                }
            )
            self.event_bus.publish(event)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"SupplierModule: Delete supplier failed: {e}")
            return {"error": str(e)}
    
    def assess_risk(self, supplier_id: int) -> Dict[str, Any]:
        """评估供应商风险"""
        try:
            # 获取供应商数据
            supplier = self.supplier_crud.get_supplier(supplier_id)
            if not supplier:
                return {"error": "Supplier not found"}
            
            # 评估风险
            risk_data = self.risk_agent.assess_risk(supplier.to_dict())
            
            # 发布风险评估事件
            event = Event(
                type=EventType.CUSTOM,
                source="supplier",
                data={
                    "event_name": "supplier.risk_assessed",
                    "supplier_id": supplier_id,
                    "risk_score": risk_data.get("risk_score")
                }
            )
            self.event_bus.publish(event)
            
            return {"data": risk_data}
        except Exception as e:
            logger.error(f"SupplierModule: Risk assessment failed: {e}")
            return {"error": str(e)}
    
    def import_suppliers(self, file_data: bytes, format: str = "excel") -> Dict[str, Any]:
        """导入供应商数据"""
        try:
            result = self.import_export.import_from_excel(file_data)
            return {"data": result}
        except Exception as e:
            logger.error(f"SupplierModule: Import failed: {e}")
            return {"error": str(e)}
    
    def export_suppliers(self, format: str = "excel") -> Dict[str, Any]:
        """导出供应商数据"""
        try:
            file_data = self.import_export.export_to_excel()
            return {
                "data": file_data,
                "filename": f"suppliers_export.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        except Exception as e:
            logger.error(f"SupplierModule: Export failed: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查数据库连接
            supplier_count = self.supplier_crud.count_suppliers()
            
            return {
                "status": "healthy",
                "message": "Supplier module is running normally",
                "details": {
                    "supplier_count": supplier_count,
                    "risk_assessment_enabled": self.config.get("enable_risk_assessment"),
                    "auto_collection_enabled": self.config.get("enable_auto_collection")
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Supplier module error: {str(e)}"
            }
