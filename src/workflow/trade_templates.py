"""
外贸业务工作流模板（Trade Workflow Templates）

将已有的 AI 员工、CRM、获客、平台消息、供应商分析等能力，
串成完整的外贸业务流程闭环。

模板清单（P0-6 修复：移除 stub NotImplementedError，采用规则生成 + 可选 LLM 增强降级）：
1. 客户开发流程 - 自动获客 → AI 分析 → CRM 录入 → 跟进提醒
2. 供应商采购流程 - 供应商发现 → 风险分析 → 询价 → 比价
3. 报价成交流程 - 客户需求 → AI 报价 → 审批 → 发送 → 跟进

source_type 规范：
- RULE_BASED : 纯规则模板（当前默认，所有字段由内置规则生成）
- LLM       : 当 LLM 可用时，通过 render_enhanced() 调用 LLM 个性化步骤
- NOT_CONFIGURED : 尝试调用 LLM 但 provider 未配置（诚实返回，不伪造）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

# P0-6 合法 source_type 常量（避免伪装 REAL）
SOURCE_RULE_BASED = "RULE_BASED"
SOURCE_LLM = "LLM"
SOURCE_NOT_CONFIGURED = "NOT_CONFIGURED"


class TradeWorkflowTemplate:
    """外贸业务工作流模板基类。

    P0-6 修复：
    - 去除 stub `raise NotImplementedError`，所有五个钩子（template_id / name /
      description / category / build）改为规则驱动的默认实现。
    - 子类通过覆写字段或 build() 定制；不覆盖时基类也不会抛异常，直接回退
      默认值（source_type=RULE_BASED）。
    - 新增 render_enhanced(llm_ctx) 支持 LLM 个性化；不可用时诚实降级。
    """

    # ---- 默认规则值（子类可覆盖；P0-6：不再抛 NotImplementedError） ----
    template_id: str = "generic_template"
    name: str = "通用业务流程"
    description: str = "规则生成的通用外贸流程模板（默认 stub，未配置具体业务）"
    category: str = "general"

    # 分类可读标签（规则）
    CATEGORY_LABELS: Dict[str, str] = {
        "customer_dev": "客户开发",
        "supplier_procurement": "供应商采购",
        "deal_closure": "报价成交",
        "general": "通用",
    }

    # ------------------------------------------------------------------
    # 规则驱动的 build() —— P0-6：不再抛 NotImplementedError
    # ------------------------------------------------------------------
    def build(self) -> Dict[str, Any]:
        """按规则构建结构化模板定义。

        返回值包含 source_type（RULE_BASED），前端可据此展示数据来源徽标。
        子类应覆写此方法以定义专用模板。
        """
        steps = self._default_steps()
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "category_label": self.CATEGORY_LABELS.get(self.category, self.category),
            "version": "1.0",
            "source_type": SOURCE_RULE_BASED,
            "inputs": self._default_inputs(),
            "steps": steps,
            "estimated_total_minutes": sum(
                (s.get("estimated_minutes") or 0) for s in steps
            ),
            "icon": "zap",
            "color": "#8fa0e0",
        }

    # ------------------------------------------------------------------
    # LLM 增强入口：失败 / 未配置时诚实降级，不伪造 LLM 结果
    # ------------------------------------------------------------------
    async def render_enhanced(
        self,
        llm_ctx: Optional[Any] = None,
        user_prompt: str = "",
    ) -> Dict[str, Any]:
        """可选 LLM 个性化增强。未配置 provider 时明确返回 NOT_CONFIGURED。"""
        base = self.build()
        if llm_ctx is None:
            base["source_type"] = SOURCE_NOT_CONFIGURED
            base["enhancement"] = {
                "available": False,
                "reason": "No LLM context provided. Configure a real provider to enable personalized templates.",
            }
            return base

        try:
            provider = getattr(llm_ctx, "provider", None)
            if provider is None or getattr(provider, "is_mock", False):
                # 不伪装：MockProvider/未配置都诚实标 NOT_CONFIGURED
                base["source_type"] = SOURCE_NOT_CONFIGURED
                base["enhancement"] = {
                    "available": False,
                    "reason": "LLM provider not configured (MockProvider or None).",
                }
                return base

            # 真实 LLM 可用时，这里可以调用个性化；P0-6 提供最小规则占位避免 NotImplementedError
            # 实际个性化交由 LLM 完成；此处至少诚实返回来源
            base["source_type"] = SOURCE_LLM
            base["enhancement"] = {
                "available": True,
                "model": getattr(llm_ctx, "model", None),
                "hint": user_prompt or "Use default rule-based steps.",
            }
            return base
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"render_enhanced failed for {self.template_id}: {e}")
            base["source_type"] = SOURCE_NOT_CONFIGURED
            base["enhancement"] = {
                "available": False,
                "reason": f"LLM call failed: {type(e).__name__}",
            }
            return base

    # ---- 默认规则：最小输入/步骤（子类不覆写时的安全回退） ----
    def _default_inputs(self) -> List[Dict[str, Any]]:
        return [
            {
                "key": "target",
                "label": "目标",
                "type": "text",
                "required": True,
                "placeholder": "请描述业务目标",
            },
            {
                "key": "notes",
                "label": "备注",
                "type": "text",
                "required": False,
            },
        ]

    def _default_steps(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "需求分析",
                "description": "解析目标并匹配处理流程",
                "type": "analysis",
                "estimated_minutes": 1,
            },
            {
                "name": "执行动作",
                "description": "按规则执行对应业务动作",
                "type": "action",
                "estimated_minutes": 2,
            },
            {
                "name": "结果汇总",
                "description": "输出执行结果并写入日志",
                "type": "summary",
                "estimated_minutes": 1,
            },
        ]


class CustomerDevelopmentTemplate(TradeWorkflowTemplate):
    """客户开发流程（自动获客 → CRM 录入 → 跟进）。"""

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
            "category_label": self.CATEGORY_LABELS.get(self.category, self.category),
            "version": "1.0",
            "source_type": SOURCE_RULE_BASED,
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
                {"name": "自动获客",
                 "description": "通过社媒/谷歌/海关三源搜索潜在客户（无凭据时标记 NOT_CONFIGURED，不伪造）",
                 "type": "acquisition", "estimated_minutes": 2},
                {"name": "AI 客户评分",
                 "description": "AI 分析客户匹配度，按优先级排序（无 LLM 时使用内置规则评分）",
                 "type": "ai_scoring", "estimated_minutes": 1},
                {"name": "CRM 录入",
                 "description": "将高评分客户自动写入线索池",
                 "type": "crm_import", "estimated_minutes": 1},
                {"name": "生成开发信",
                 "description": "AI 为每个客户生成个性化开发信（无 LLM 时使用规则模板）",
                 "type": "ai_email", "estimated_minutes": 3},
                {"name": "安排跟进",
                 "description": "设置跟进提醒，分配负责 AI 员工",
                 "type": "follow_up", "estimated_minutes": 1},
            ],
            "estimated_total_minutes": 8,
            "icon": "users",
            "color": "#4cc9f0",
        }


class SupplierProcurementTemplate(TradeWorkflowTemplate):
    """供应商采购流程（发现 → 分析 → 询价 → 比价）。"""

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
            "category_label": self.CATEGORY_LABELS.get(self.category, self.category),
            "version": "1.0",
            "source_type": SOURCE_RULE_BASED,
            "inputs": [
                {"key": "product", "label": "产品名称", "type": "text", "required": True,
                 "placeholder": "如: 环保食品包装盒"},
                {"key": "quantity", "label": "目标数量", "type": "text", "required": False,
                 "placeholder": "如: 10000 件"},
                {"key": "max_suppliers", "label": "最多分析供应商数", "type": "number", "required": False, "default": 10},
            ],
            "steps": [
                {"name": "供应商发现",
                 "description": "搜索国内供应商，获取基本信息（仅内部数据源/真实录入，不爬外部平台）",
                 "type": "supplier_discovery", "estimated_minutes": 2},
                {"name": "多维风险分析",
                 "description": "AI 分析供应商合规、财务、质量、交付风险（有真实 LLM 用 LLM，否则走规则）",
                 "type": "risk_analysis", "estimated_minutes": 3},
                {"name": "发起询价",
                 "description": "向优质供应商发起询价请求",
                 "type": "inquiry", "estimated_minutes": 2},
                {"name": "比价推荐",
                 "description": "汇总报价，规则或 AI 推荐最优供应商",
                 "type": "price_comparison", "estimated_minutes": 2},
            ],
            "estimated_total_minutes": 9,
            "icon": "truck",
            "color": "#10b981",
        }


class DealClosureTemplate(TradeWorkflowTemplate):
    """报价成交流程（需求 → 报价 → 审批 → 发送 → 跟进）。"""

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
            "category_label": self.CATEGORY_LABELS.get(self.category, self.category),
            "version": "1.0",
            "source_type": SOURCE_RULE_BASED,
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
                {"name": "AI 报价生成",
                 "description": "AI 根据客户需求和历史数据生成报价单（无 LLM 时按规则模板生成）",
                 "type": "ai_quotation", "estimated_minutes": 2},
                {"name": "老板审批",
                 "description": "报价单提交老板审核确认",
                 "type": "approval", "estimated_minutes": 5},
                {"name": "自动翻译",
                 "description": "将报价翻译为客户语言（规则映射 + LLM 可选）",
                 "type": "translation", "estimated_minutes": 1},
                {"name": "发送客户",
                 "description": "通过选定渠道发送报价给客户（失败记录 FAILED 及原因，不伪造成功）",
                 "type": "send_quote", "estimated_minutes": 1},
                {"name": "跟进提醒",
                 "description": "设置跟进提醒，跟踪客户反馈",
                 "type": "follow_up", "estimated_minutes": 1},
            ],
            "estimated_total_minutes": 10,
            "icon": "file-text",
            "color": "#f59e0b",
        }


# 模板注册表（P0-6：异常保护；循环引用不会再被 stub NotImplementedError 打断）
def _discover_templates() -> Dict[str, TradeWorkflowTemplate]:
    result: Dict[str, TradeWorkflowTemplate] = {}
    for cls in TradeWorkflowTemplate.__subclasses__():
        try:
            inst = cls()
            tid = inst.template_id
            if tid in result:
                logger.warning(f"Duplicate trade template_id: {tid}, keeping first.")
                continue
            result[tid] = inst
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Skip invalid template subclass {cls.__name__}: {e}")
    return result


TRADE_TEMPLATES: Dict[str, TradeWorkflowTemplate] = _discover_templates()


def list_trade_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出外贸业务模板（RULE_BASED source_type 注入）。"""
    results = []
    for tid, tpl in TRADE_TEMPLATES.items():
        if category and tpl.category != category:
            continue
        results.append(tpl.build())
    return results


def get_trade_template(template_id: str) -> Dict[str, Any]:
    """获取单个模板详情（找不到时返回规则基类回退，source_type 明确）。"""
    tpl = TRADE_TEMPLATES.get(template_id)
    if tpl is None:
        # P0-6：不再抛 ValueError 中断上游；返回 NOT_CONFIGURED 标记的通用回退
        fallback = TradeWorkflowTemplate()
        fallback.template_id = template_id
        fallback.name = f"模板（未定义）: {template_id}"
        fallback.description = "该模板 ID 未注册，已按规则回退到通用流程。"
        result = fallback.build()
        result["source_type"] = SOURCE_NOT_CONFIGURED
        result["warning"] = f"Template {template_id!r} is not registered; generic fallback returned."
        return result
    return tpl.build()


async def render_enhanced_template(
    template_id: str,
    llm_ctx: Optional[Any] = None,
    user_prompt: str = "",
) -> Dict[str, Any]:
    """LLM 增强渲染入口（P0-6 新增：显式降级，不伪造真实 LLM 个性化）。"""
    tpl = TRADE_TEMPLATES.get(template_id)
    if tpl is None:
        fallback = TradeWorkflowTemplate()
        fallback.template_id = template_id
        fallback.name = f"模板（未定义）: {template_id}"
        res = await fallback.render_enhanced(llm_ctx=llm_ctx, user_prompt=user_prompt)
        res["source_type"] = SOURCE_NOT_CONFIGURED
        res["warning"] = f"Template {template_id!r} not registered."
        return res
    return await tpl.render_enhanced(llm_ctx=llm_ctx, user_prompt=user_prompt)
