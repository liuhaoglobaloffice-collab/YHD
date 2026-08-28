"""
外贸业务工作流模板（Trade Workflow Templates）

将已有的 AI 员工、CRM、获客、平台消息、供应商分析等能力，
串成完整的外贸业务流程闭环。

模板清单：
1. 客户开发流程 - 自动获客 → AI 分析 → CRM 录入 → 跟进提醒
2. 供应商采购流程 - 供应商发现 → 风险分析 → 询价 → 比价
3. 报价成交流程 - 客户需求 → AI 报价 → 审批 → 发送 → 跟进
"""

from typing import Any, Dict, List


class TradeWorkflowTemplate:
    """外贸业务工作流模板基类"""

    @property
    def template_id(self) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    @property
    def category(self) -> str:
        """分类: customer_dev / supplier_procurement / deal_closure"""
        raise NotImplementedError

    def build(self) -> Dict[str, Any]:
        raise NotImplementedError


class CustomerDevelopmentTemplate(TradeWorkflowTemplate):
    """
    客户开发流程（自动获客 → CRM 录入 → 跟进）
    
    适用场景：老板想开发新市场/新产品线的客户
    触发方式：输入目标市场、产品关键词、国家
    """

    template_id = "customer_development"
    name = "客户开发流程"
    description = "AI 自动搜索目标客户 → 分析评分 → 录入 CRM → 生成开发信 → 安排跟进"
    category = "customer_dev"

    def build(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": "1.0",
            "inputs": [
                {"key": "keywords", "label": "产品关键词", "type": "text", "required": True,
                 "placeholder": "如: LED light, food packaging"},
                {"key": "target_countries", "label": "目标国家", "type": "text", "required": False,
                 "placeholder": "如: USA, Germany（逗号分隔）"},
                {"key": "lead_count", "label": "目标线索数", "type": "number", "required": False, "default": 20},
                {"key": "sources", "label": "数据来源", "type": "multi_select", "required": False,
                 "options": ["social", "google", "customs"], "default": ["social", "google", "customs"]},
            ],
            "steps": [
                {
                    "name": "自动获客",
                    "description": "通过社媒/谷歌/海关三源搜索潜在客户",
                    "type": "acquisition",
                    "estimated_minutes": 2,
                },
                {
                    "name": "AI 客户评分",
                    "description": "AI 分析客户匹配度，按优先级排序",
                    "type": "ai_scoring",
                    "estimated_minutes": 1,
                },
                {
                    "name": "CRM 录入",
                    "description": "将高评分客户自动写入线索池",
                    "type": "crm_import",
                    "estimated_minutes": 1,
                },
                {
                    "name": "生成开发信",
                    "description": "AI 为每个客户生成个性化开发信",
                    "type": "ai_email",
                    "estimated_minutes": 3,
                },
                {
                    "name": "安排跟进",
                    "description": "设置跟进提醒，分配负责 AI 员工",
                    "type": "follow_up",
                    "estimated_minutes": 1,
                },
            ],
            "estimated_total_minutes": 8,
            "icon": "users",
            "color": "#4cc9f0",
        }


class SupplierProcurementTemplate(TradeWorkflowTemplate):
    """
    供应商采购流程（发现 → 分析 → 询价 → 比价）
    
    适用场景：需要寻找新供应商或对比多家供应商
    触发方式：输入产品名称、要求数量
    """

    template_id = "supplier_procurement"
    name = "供应商采购流程"
    description = "搜索国内供应商 → 风险/价格/产能分析 → 发起询价 → 比价推荐"
    category = "supplier_procurement"

    def build(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": "1.0",
            "inputs": [
                {"key": "product", "label": "产品名称", "type": "text", "required": True,
                 "placeholder": "如: 环保食品包装盒"},
                {"key": "quantity", "label": "目标数量", "type": "text", "required": False,
                 "placeholder": "如: 10000 件"},
                {"key": "max_suppliers", "label": "最多分析供应商数", "type": "number", "required": False, "default": 10},
            ],
            "steps": [
                {
                    "name": "供应商发现",
                    "description": "搜索国内供应商，获取基本信息",
                    "type": "supplier_discovery",
                    "estimated_minutes": 2,
                },
                {
                    "name": "多维风险分析",
                    "description": "AI 分析供应商合规、财务、质量、交付风险",
                    "type": "risk_analysis",
                    "estimated_minutes": 3,
                },
                {
                    "name": "发起询价",
                    "description": "向优质供应商发起询价请求",
                    "type": "inquiry",
                    "estimated_minutes": 2,
                },
                {
                    "name": "比价推荐",
                    "description": "汇总报价，AI 推荐最优供应商",
                    "type": "price_comparison",
                    "estimated_minutes": 2,
                },
            ],
            "estimated_total_minutes": 9,
            "icon": "truck",
            "color": "#10b981",
        }


class DealClosureTemplate(TradeWorkflowTemplate):
    """
    报价成交流程（需求 → 报价 → 审批 → 发送 → 跟进）
    
    适用场景：客户询价后需要快速生成报价并跟进
    触发方式：选择客户，输入产品需求和预算
    """

    template_id = "deal_closure"
    name = "报价成交流程"
    description = "AI 分析客户需求 → 生成报价单 → 老板审批 → 发送客户 → 跟进成交"
    category = "deal_closure"

    def build(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": "1.0",
            "inputs": [
                {"key": "lead_id", "label": "选择客户", "type": "lead_select", "required": True,
                 "placeholder": "从 CRM 中选择客户"},
                {"key": "product", "label": "产品/需求", "type": "text", "required": True,
                 "placeholder": "客户需求的产品描述"},
                {"key": "budget", "label": "客户预算 (USD)", "type": "number", "required": False},
                {"key": "target_lang", "label": "报价语言", "type": "lang_select", "required": False, "default": "en"},
                {"key": "send_via", "label": "发送渠道", "type": "multi_select", "required": False,
                 "options": ["email", "whatsapp", "linkedin"], "default": ["email"]},
            ],
            "steps": [
                {
                    "name": "AI 报价生成",
                    "description": "AI 根据客户需求和历史数据生成报价单",
                    "type": "ai_quotation",
                    "estimated_minutes": 2,
                },
                {
                    "name": "老板审批",
                    "description": "报价单提交老板审核确认",
                    "type": "approval",
                    "estimated_minutes": 5,
                },
                {
                    "name": "自动翻译",
                    "description": "将报价翻译为客户语言",
                    "type": "translation",
                    "estimated_minutes": 1,
                },
                {
                    "name": "发送客户",
                    "description": "通过选定渠道发送报价给客户",
                    "type": "send_quote",
                    "estimated_minutes": 1,
                },
                {
                    "name": "跟进提醒",
                    "description": "设置跟进提醒，跟踪客户反馈",
                    "type": "follow_up",
                    "estimated_minutes": 1,
                },
            ],
            "estimated_total_minutes": 10,
            "icon": "file-text",
            "color": "#f59e0b",
        }


# 模板注册表
TRADE_TEMPLATES: Dict[str, TradeWorkflowTemplate] = {
    cls().template_id: cls()
    for cls in TradeWorkflowTemplate.__subclasses__()
}


def list_trade_templates(category: str = None) -> List[Dict[str, Any]]:
    """列出外贸业务模板"""
    results = []
    for tid, tpl in TRADE_TEMPLATES.items():
        if category and tpl.category != category:
            continue
        results.append(tpl.build())
    return results


def get_trade_template(template_id: str) -> Dict[str, Any]:
    """获取单个模板详情"""
    tpl = TRADE_TEMPLATES.get(template_id)
    if not tpl:
        raise ValueError(f"模板不存在: {template_id}")
    return tpl.build()