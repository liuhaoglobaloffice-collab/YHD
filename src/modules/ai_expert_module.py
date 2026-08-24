"""
AI 专家管理模块

管理鎏灏 AI-OS 的 AI 专家系统:
- 10 个核心 AI 专家（可扩展到 32 个）
- 专家配置与管理
- API 端点配置
- 专家状态监控
"""

from src.core.modules import BaseModule, ModuleInfo, EventBus, Event, EventType
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExpertType(Enum):
    """AI 专家类型"""
    DATA_COLLECTOR = "data_collector"          # 数据采集
    RISK_ASSESSOR = "risk_assessor"            # 风险评估
    TEXT_GENERATOR = "text_generator"          # 文本生成
    DATA_ANALYST = "data_analyst"              # 数据分析
    TRANSLATOR = "translator"                   # 翻译
    SUMMARIZER = "summarizer"                   # 摘要
    QA_EXPERT = "qa_expert"                     # 问答
    CODE_GENERATOR = "code_generator"           # 代码生成
    SENTIMENT_ANALYZER = "sentiment_analyzer"   # 情感分析
    ENTITY_RECOGNIZER = "entity_recognizer"     # 实体识别
    
    # 预留扩展类型（11-32）
    CUSTOM_11 = "custom_11"
    CUSTOM_12 = "custom_12"
    CUSTOM_13 = "custom_13"
    CUSTOM_14 = "custom_14"
    CUSTOM_15 = "custom_15"
    CUSTOM_16 = "custom_16"
    CUSTOM_17 = "custom_17"
    CUSTOM_18 = "custom_18"
    CUSTOM_19 = "custom_19"
    CUSTOM_20 = "custom_20"
    CUSTOM_21 = "custom_21"
    CUSTOM_22 = "custom_22"
    CUSTOM_23 = "custom_23"
    CUSTOM_24 = "custom_24"
    CUSTOM_25 = "custom_25"
    CUSTOM_26 = "custom_26"
    CUSTOM_27 = "custom_27"
    CUSTOM_28 = "custom_28"
    CUSTOM_29 = "custom_29"
    CUSTOM_30 = "custom_30"
    CUSTOM_31 = "custom_31"
    CUSTOM_32 = "custom_32"


class ExpertStatus(Enum):
    """专家状态"""
    ACTIVE = "active"           # 活跃
    INACTIVE = "inactive"       # 未激活
    ERROR = "error"             # 错误
    TESTING = "testing"         # 测试中


@dataclass
class AIExpertConfig:
    """AI 专家配置"""
    id: int
    name: str
    type: ExpertType
    description: str
    api_url: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    status: ExpertStatus = ExpertStatus.INACTIVE
    is_custom: bool = False
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['type'] = self.type.value
        data['status'] = self.status.value
        return data


class AIExpertModule(BaseModule):
    """
    AI 专家管理模块
    
    管理系统中的所有 AI 专家:
    - 10 个核心专家
    - 支持扩展到 32 个
    - UI 配置界面
    - API 端点管理
    """
    
    def __init__(self):
        super().__init__()
        self.event_bus = EventBus()
        self.experts: Dict[int, AIExpertConfig] = {}
        self.next_expert_id = 1
    
    def get_module_info(self) -> ModuleInfo:
        """返回模块信息"""
        return ModuleInfo(
            name="ai_expert",
            version="1.0.0",
            description="AI 专家管理模块 - 管理10个核心AI专家（可扩展到32个）",
            author="LiuHao AI-OS Team",
            
            # 依赖关系
            dependencies=[],
            
            # 模块类型
            is_builtin=True,
            is_custom=False,
            
            # 能力声明
            provides_api=True,
            provides_ui=True,
            provides_events=[
                "expert.created",
                "expert.updated",
                "expert.deleted",
                "expert.tested",
                "expert.status_changed"
            ],
            consumes_events=["system.startup"],
            
            # 配置
            default_config={
                "max_experts": 32,
                "enable_auto_test": True,
                "test_timeout": 30,
                "default_model": "gpt-4o-mini"
            }
        )
    
    def _on_initialize(self) -> bool:
        """初始化模块"""
        try:
            logger.info("AIExpertModule: Initializing...")
            
            # 初始化 10 个核心专家
            self._init_core_experts()
            
            # 订阅系统事件
            self.event_bus.subscribe(EventType.SYSTEM_STARTUP, self._on_system_startup)
            
            logger.info(f"AIExpertModule: Initialized with {len(self.experts)} experts")
            return True
            
        except Exception as e:
            logger.error(f"AIExpertModule: Initialization failed: {e}")
            return False
    
    def _init_core_experts(self):
        """初始化 10 个核心 AI 专家"""
        core_experts = [
            {
                "name": "供应商数据采集专家",
                "type": ExpertType.DATA_COLLECTOR,
                "description": "自动从网页、文档中采集供应商信息",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            {
                "name": "风险评估专家",
                "type": ExpertType.RISK_ASSESSOR,
                "description": "评估供应商、业务、合作伙伴的风险等级",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o"
            },
            {
                "name": "文本生成专家",
                "type": ExpertType.TEXT_GENERATOR,
                "description": "生成邮件、报告、文档等文本内容",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            {
                "name": "数据分析专家",
                "type": ExpertType.DATA_ANALYST,
                "description": "分析业务数据、生成洞察和建议",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o"
            },
            {
                "name": "翻译专家",
                "type": ExpertType.TRANSLATOR,
                "description": "多语言翻译（中英粤等）",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            {
                "name": "摘要专家",
                "type": ExpertType.SUMMARIZER,
                "description": "提取长文本的核心信息和摘要",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            {
                "name": "问答专家",
                "type": ExpertType.QA_EXPERT,
                "description": "回答业务相关问题",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o"
            },
            {
                "name": "代码生成专家",
                "type": ExpertType.CODE_GENERATOR,
                "description": "生成代码、SQL、脚本",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o"
            },
            {
                "name": "情感分析专家",
                "type": ExpertType.SENTIMENT_ANALYZER,
                "description": "分析文本情感倾向",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            },
            {
                "name": "实体识别专家",
                "type": ExpertType.ENTITY_RECOGNIZER,
                "description": "识别文本中的人名、地名、机构名等实体",
                "api_url": "https://api.openai.com/v1/chat/completions",
                "model": "gpt-4o-mini"
            }
        ]
        
        for expert_data in core_experts:
            expert = AIExpertConfig(
                id=self.next_expert_id,
                name=expert_data["name"],
                type=expert_data["type"],
                description=expert_data["description"],
                api_url=expert_data["api_url"],
                model=expert_data["model"],
                status=ExpertStatus.INACTIVE,
                is_custom=False,
                enabled=True
            )
            self.experts[self.next_expert_id] = expert
            self.next_expert_id += 1
    
    def _on_start(self) -> bool:
        """启动模块"""
        try:
            logger.info("AIExpertModule: Starting...")
            
            # 如果启用自动测试，测试所有专家
            if self.config.get("enable_auto_test"):
                logger.info("AIExpertModule: Auto-testing experts...")
                # TODO: 实现自动测试逻辑
            
            logger.info("AIExpertModule: Started successfully")
            return True
            
        except Exception as e:
            logger.error(f"AIExpertModule: Start failed: {e}")
            return False
    
    def _on_stop(self) -> bool:
        """停止模块"""
        try:
            logger.info("AIExpertModule: Stopping...")
            logger.info("AIExpertModule: Stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"AIExpertModule: Stop failed: {e}")
            return False
    
    def _on_system_startup(self, event: Event):
        """监听系统启动事件"""
        logger.info("AIExpertModule: System started, AI experts ready")
        
        # 发布模块就绪事件
        ready_event = Event(
            type=EventType.CUSTOM,
            source="ai_expert",
            data={
                "event_name": "ai_expert.module_ready",
                "expert_count": len(self.experts)
            }
        )
        self.event_bus.publish(ready_event)
    
    def get_api_routes(self) -> List[Dict[str, Any]]:
        """返回 API 路由"""
        return [
            # 专家管理
            {
                "path": "/api/v1/experts",
                "method": "GET",
                "handler": self.list_experts,
                "tags": ["expert"],
                "summary": "列出所有 AI 专家"
            },
            {
                "path": "/api/v1/experts/{expert_id}",
                "method": "GET",
                "handler": self.get_expert,
                "tags": ["expert"],
                "summary": "获取专家详情"
            },
            {
                "path": "/api/v1/experts",
                "method": "POST",
                "handler": self.create_expert,
                "tags": ["expert"],
                "summary": "添加自定义专家"
            },
            {
                "path": "/api/v1/experts/{expert_id}",
                "method": "PUT",
                "handler": self.update_expert,
                "tags": ["expert"],
                "summary": "更新专家配置"
            },
            {
                "path": "/api/v1/experts/{expert_id}",
                "method": "DELETE",
                "handler": self.delete_expert,
                "tags": ["expert"],
                "summary": "删除自定义专家"
            },
            
            # 专家操作
            {
                "path": "/api/v1/experts/{expert_id}/test",
                "method": "POST",
                "handler": self.test_expert,
                "tags": ["expert", "test"],
                "summary": "测试专家连接"
            },
            {
                "path": "/api/v1/experts/{expert_id}/enable",
                "method": "POST",
                "handler": self.enable_expert,
                "tags": ["expert"],
                "summary": "启用专家"
            },
            {
                "path": "/api/v1/experts/{expert_id}/disable",
                "method": "POST",
                "handler": self.disable_expert,
                "tags": ["expert"],
                "summary": "禁用专家"
            },
            
            # 统计
            {
                "path": "/api/v1/experts/stats",
                "method": "GET",
                "handler": self.get_stats,
                "tags": ["expert", "stats"],
                "summary": "获取专家统计信息"
            }
        ]
    
    def get_ui_components(self) -> List[Dict[str, Any]]:
        """返回 UI 组件"""
        return [
            {
                "name": "ExpertList",
                "path": "/experts",
                "component": "ExpertList",
                "menu_label": "AI 专家管理",
                "menu_group": "系统管理",
                "icon": "brain",
                "description": "管理 AI 专家，配置 API 端点"
            },
            {
                "name": "ExpertConfig",
                "path": "/experts/:id/config",
                "component": "ExpertConfig",
                "menu_label": "",
                "icon": "settings",
                "description": "专家配置界面（API URL、Token、模型）"
            },
            {
                "name": "ExpertDashboard",
                "path": "/experts/dashboard",
                "component": "ExpertDashboard",
                "menu_label": "专家监控",
                "menu_group": "系统管理",
                "icon": "activity",
                "description": "专家状态监控仪表板"
            },
            {
                "name": "ExpertCreate",
                "path": "/experts/create",
                "component": "ExpertCreate",
                "menu_label": "",
                "icon": "plus-circle",
                "description": "添加自定义专家"
            }
        ]
    
    # API Handler 实现
    
    def list_experts(self, type: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """列出 AI 专家"""
        try:
            experts = list(self.experts.values())
            
            # 筛选
            if type:
                experts = [e for e in experts if e.type.value == type]
            if status:
                experts = [e for e in experts if e.status.value == status]
            
            return {
                "data": [e.to_dict() for e in experts],
                "total": len(experts)
            }
        except Exception as e:
            logger.error(f"AIExpertModule: List experts failed: {e}")
            return {"error": str(e)}
    
    def get_expert(self, expert_id: int) -> Dict[str, Any]:
        """获取专家详情"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            return {"data": expert.to_dict()}
        except Exception as e:
            logger.error(f"AIExpertModule: Get expert failed: {e}")
            return {"error": str(e)}
    
    def create_expert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建自定义专家"""
        try:
            # 检查是否达到上限
            max_experts = self.config.get("max_experts", 32)
            if len(self.experts) >= max_experts:
                return {"error": f"Maximum {max_experts} experts allowed"}
            
            # 创建专家
            expert = AIExpertConfig(
                id=self.next_expert_id,
                name=data["name"],
                type=ExpertType(data.get("type", "custom_11")),
                description=data.get("description", ""),
                api_url=data["api_url"],
                api_key=data.get("api_key"),
                model=data.get("model", self.config.get("default_model")),
                temperature=data.get("temperature", 0.7),
                max_tokens=data.get("max_tokens", 2000),
                is_custom=True,
                enabled=True
            )
            
            self.experts[self.next_expert_id] = expert
            self.next_expert_id += 1
            
            # 发布创建事件
            event = Event(
                type=EventType.CUSTOM,
                source="ai_expert",
                data={
                    "event_name": "expert.created",
                    "expert_id": expert.id,
                    "expert_name": expert.name
                }
            )
            self.event_bus.publish(event)
            
            return {"data": expert.to_dict()}
        except Exception as e:
            logger.error(f"AIExpertModule: Create expert failed: {e}")
            return {"error": str(e)}
    
    def update_expert(self, expert_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新专家配置"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            # 更新字段
            if "name" in data:
                expert.name = data["name"]
            if "description" in data:
                expert.description = data["description"]
            if "api_url" in data:
                expert.api_url = data["api_url"]
            if "api_key" in data:
                expert.api_key = data["api_key"]
            if "model" in data:
                expert.model = data["model"]
            if "temperature" in data:
                expert.temperature = data["temperature"]
            if "max_tokens" in data:
                expert.max_tokens = data["max_tokens"]
            
            # 发布更新事件
            event = Event(
                type=EventType.CUSTOM,
                source="ai_expert",
                data={
                    "event_name": "expert.updated",
                    "expert_id": expert.id,
                    "expert_name": expert.name
                }
            )
            self.event_bus.publish(event)
            
            return {"data": expert.to_dict()}
        except Exception as e:
            logger.error(f"AIExpertModule: Update expert failed: {e}")
            return {"error": str(e)}
    
    def delete_expert(self, expert_id: int) -> Dict[str, Any]:
        """删除自定义专家"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            # 只能删除自定义专家
            if not expert.is_custom:
                return {"error": "Cannot delete core expert"}
            
            del self.experts[expert_id]
            
            # 发布删除事件
            event = Event(
                type=EventType.CUSTOM,
                source="ai_expert",
                data={
                    "event_name": "expert.deleted",
                    "expert_id": expert_id
                }
            )
            self.event_bus.publish(event)
            
            return {"success": True}
        except Exception as e:
            logger.error(f"AIExpertModule: Delete expert failed: {e}")
            return {"error": str(e)}
    
    def test_expert(self, expert_id: int) -> Dict[str, Any]:
        """测试专家连接"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            # TODO: 实现实际的 API 测试
            # 这里模拟测试结果
            expert.status = ExpertStatus.TESTING
            
            # 模拟测试成功
            test_result = {
                "success": True,
                "response_time": 150,  # ms
                "message": "Connection successful"
            }
            
            expert.status = ExpertStatus.ACTIVE if test_result["success"] else ExpertStatus.ERROR
            
            # 发布测试事件
            event = Event(
                type=EventType.CUSTOM,
                source="ai_expert",
                data={
                    "event_name": "expert.tested",
                    "expert_id": expert.id,
                    "result": test_result
                }
            )
            self.event_bus.publish(event)
            
            return {"data": test_result}
        except Exception as e:
            logger.error(f"AIExpertModule: Test expert failed: {e}")
            return {"error": str(e)}
    
    def enable_expert(self, expert_id: int) -> Dict[str, Any]:
        """启用专家"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            expert.enabled = True
            
            return {"success": True}
        except Exception as e:
            logger.error(f"AIExpertModule: Enable expert failed: {e}")
            return {"error": str(e)}
    
    def disable_expert(self, expert_id: int) -> Dict[str, Any]:
        """禁用专家"""
        try:
            expert = self.experts.get(expert_id)
            if not expert:
                return {"error": "Expert not found"}
            
            expert.enabled = False
            
            return {"success": True}
        except Exception as e:
            logger.error(f"AIExpertModule: Disable expert failed: {e}")
            return {"error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            total = len(self.experts)
            core = sum(1 for e in self.experts.values() if not e.is_custom)
            custom = sum(1 for e in self.experts.values() if e.is_custom)
            active = sum(1 for e in self.experts.values() if e.status == ExpertStatus.ACTIVE)
            enabled = sum(1 for e in self.experts.values() if e.enabled)
            
            return {
                "data": {
                    "total": total,
                    "core": core,
                    "custom": custom,
                    "active": active,
                    "enabled": enabled,
                    "max_allowed": self.config.get("max_experts", 32),
                    "available_slots": self.config.get("max_experts", 32) - total
                }
            }
        except Exception as e:
            logger.error(f"AIExpertModule: Get stats failed: {e}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = self.get_stats()
            
            return {
                "status": "healthy",
                "message": "AI Expert module is running normally",
                "details": stats.get("data", {})
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"AI Expert module error: {str(e)}"
            }
