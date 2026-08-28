"""
S2 多平台接入 - 消息模板管理

定义各平台消息模板（尤其是 WhatsApp 模板消息），
提供模板创建、列表、发送功能。
模板数据存储在平台账号的 meta 字段或独立配置中。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==================== 预置模板定义 ====================

WHATSAPP_TEMPLATES = {
    "welcome": {
        "name": "welcome_message",
        "language": "zh_CN",
        "category": "MARKETING",
        "components": [
            {
                "type": "HEADER",
                "format": "TEXT",
                "text": "欢迎 {{1}}",
            },
            {
                "type": "BODY",
                "text": "您好 {{1}}，感谢您联系 {{2}}！\n\n"
                        "我们已收到您的消息，将在 24 小时内回复。\n\n"
                        "如需加急处理，请回复「加急」。",
            },
            {
                "type": "FOOTER",
                "text": "鎏灏 AI OS - 智能外贸助手",
            },
        ],
        "example": {
            "header_text": ["客户"],
            "body_text": [
                ["客户", "鎏灏科技"],
            ],
        },
    },
    "order_confirmation": {
        "name": "order_confirmation",
        "language": "zh_CN",
        "category": "UTILITY",
        "components": [
            {
                "type": "HEADER",
                "format": "TEXT",
                "text": "订单确认 #{{1}}",
            },
            {
                "type": "BODY",
                "text": "尊敬的 {{1}}，您的订单 {{2}} 已确认。\n\n"
                        "订单金额: {{3}}\n"
                        "预计发货: {{4}}\n\n"
                        "我们将及时更新物流信息。",
            },
        ],
        "example": {
            "header_text": ["ORD-2024-0001"],
            "body_text": [
                ["客户", "ORD-2024-0001", "¥1,200.00", "2024-03-01"],
            ],
        },
    },
    "shipping_update": {
        "name": "shipping_update",
        "language": "zh_CN",
        "category": "UTILITY",
        "components": [
            {
                "type": "HEADER",
                "format": "TEXT",
                "text": "物流更新",
            },
            {
                "type": "BODY",
                "text": "您好 {{1}}，您的订单 {{2}} 已发货。\n\n"
                        "物流单号: {{3}}\n"
                        "预计送达: {{4}}\n\n"
                        "点击查看物流详情。",
            },
        ],
        "example": {
            "header_text": [""],
            "body_text": [
                ["客户", "ORD-2024-0001", "SF1234567890", "2024-03-05"],
            ],
        },
    },
    "inquiry_received": {
        "name": "inquiry_received",
        "language": "zh_CN",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "您好 {{1}}，我们已收到您的询价请求。\n\n"
                        "询价商品: {{2}}\n"
                        "数量: {{3}}\n\n"
                        "销售团队正在准备报价，将尽快回复您。",
            },
        ],
        "example": {
            "body_text": [
                ["客户", "不锈钢管 304", "500 件"],
            ],
        },
    },
}


# ==================== 模板管理服务 ====================


@dataclass
class MessageTemplate:
    """消息模板"""
    name: str
    category: str  # MARKETING / UTILITY / AUTHENTICATION
    language: str
    components: List[Dict[str, Any]]
    example: Optional[Dict[str, Any]] = None
    platform: str = "whatsapp"
    id: Optional[int] = None
    variables: int = field(init=False)

    def __post_init__(self):
        # 估算模板变量数量
        self.variables = 0
        for comp in self.components:
            text = comp.get("text", "")
            count = 0
            i = 0
            while i < len(text):
                if text[i : i + 2] == "{{":
                    end = text.find("}}", i)
                    if end > i:
                        # 提取变量序号
                        var_num = text[i + 2 : end].strip()
                        try:
                            num = int(var_num)
                            count = max(count, num)
                        except ValueError:
                            pass
                        i = end + 2
                        continue
                i += 1
            self.variables = max(self.variables, count)


class TemplateService:
    """消息模板管理服务"""

    def __init__(self):
        self._presets = self._load_presets()

    def _load_presets(self) -> Dict[str, MessageTemplate]:
        """加载预置模板"""
        presets = {}
        for key, data in WHATSAPP_TEMPLATES.items():
            presets[key] = MessageTemplate(
                name=data["name"],
                category=data["category"],
                language=data["language"],
                components=data["components"],
                example=data.get("example"),
            )
        return presets

    def list_presets(self, platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出预置模板"""
        result = []
        for key, tpl in self._presets.items():
            if platform and tpl.platform != platform:
                continue
            result.append({
                "id": key,
                "name": tpl.name,
                "category": tpl.category,
                "language": tpl.language,
                "platform": tpl.platform,
                "variables": tpl.variables,
                "components": tpl.components,
                "example": tpl.example,
            })
        return result

    def get_preset(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取预置模板详情"""
        tpl = self._presets.get(template_id)
        if not tpl:
            return None
        return {
            "id": template_id,
            "name": tpl.name,
            "category": tpl.category,
            "language": tpl.language,
            "platform": tpl.platform,
            "variables": tpl.variables,
            "components": tpl.components,
            "example": tpl.example,
        }

    def render_template(
        self, template_id: str, variables: Dict[str, str]
    ) -> Optional[str]:
        """渲染模板为文本（用于 Mock 模式或预览）。"""
        tpl = self._presets.get(template_id)
        if not tpl:
            return None

        body_text = ""
        for comp in tpl.components:
            if comp.get("type") == "BODY":
                body_text = comp.get("text", "")
                break

        # 替换变量
        for key, value in variables.items():
            body_text = body_text.replace("{{" + key + "}}", value)

        return body_text