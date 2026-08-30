"""
CEO Command Processor - Phase 3.1 AI Brain Core

Processes natural language commands from CEO and converts them to
structured ParsedCommand for planning.

P0-1: `parse_with_llm()` adds real LLM goal understanding on top of the
rule-based baseline — the boss's one-sentence goal is decomposed into
KPI / budget / time range / risk boundaries via the Provider Gateway,
with an honest fallback to the rule parser when no Provider is
configured (metadata.parse_method marks "llm" vs "rule_based").
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .models import CommandPriority, ParsedCommand

logger = logging.getLogger(__name__)


class CEOCommandProcessor:
    """
    Processes CEO natural language commands.

    Responsibilities:
    - Parse natural language input
    - Extract goal and constraints
    - Determine priority and complexity
    - Identify required agent types
    """

    # Keyword-based agent routing (simple heuristics for Phase 3.1)
    AGENT_KEYWORDS = {
        "research": ["研究", "调研", "分析", "research", "analyze", "investigate"],
        "marketing": ["营销", "市场", "推广", "SEO", "marketing", "promote"],
        "sales": ["销售", "客户", "开发", "CRM", "sales", "customer", "lead"],
        "business": ["业务", "运营", "管理", "business", "operation", "manage"],
        "ceo_assistant": ["战略", "决策", "汇报", "strategy", "decision", "report"],
    }

    PRIORITY_KEYWORDS = {
        CommandPriority.CRITICAL: ["紧急", "立即", "urgent", "critical", "asap"],
        CommandPriority.HIGH: ["重要", "优先", "高优", "important", "priority", "high"],
        CommandPriority.LOW: ["低", "不急", "low", "later", "when possible"],
    }

    COMPLEXITY_KEYWORDS = {
        "high": ["复杂", "详细", "全面", "深入", "complex", "detailed", "comprehensive", "deep"],
        "low": ["简单", "快速", "基本", "simple", "quick", "basic"],
    }

    def __init__(self):
        logger.info("CEOCommandProcessor initialized")

    def parse(self, command_text: str, context: Optional[Dict] = None) -> ParsedCommand:
        """
        Parse CEO command into structured format.

        Args:
            command_text: Natural language command
            context: Optional context (user preferences, history, etc.)

        Returns:
            ParsedCommand with extracted information
        """
        # Validate input
        if not command_text:
            raise ValueError("Command text cannot be empty")
        if not isinstance(command_text, str):
            raise TypeError("Command text must be a string")

        # Extract goal (main objective)
        goal = self._extract_goal(command_text)

        # Extract constraints (地域、行业、时间等限制)
        constraints = self._extract_constraints(command_text)

        # Determine priority
        priority = self._determine_priority(command_text)

        # Estimate complexity
        complexity = self._estimate_complexity(command_text)

        # Identify required agents
        required_agents = self._identify_required_agents(command_text)

        parsed = ParsedCommand(
            goal=goal,
            constraints=constraints,
            context=context or {},
            priority=priority,
            estimated_complexity=complexity,
            required_agents=required_agents,
            metadata={
                "original_command": command_text,
                "language": self._detect_language(command_text),
            },
        )

        logger.info(
            f"Parsed CEO command: goal='{goal}', "
            f"agents={required_agents}, priority={priority.value}"
        )

        return parsed

    def _extract_goal(self, command: str) -> str:
        """
        Extract main goal from command.

        For Phase 3.1, we use simple extraction (first sentence or full text).
        Future: Use NLP/LLM for better goal extraction.
        """
        # Remove leading/trailing whitespace
        command = command.strip()

        # If command has multiple sentences, use first as goal
        sentences = re.split(r"[。！？.!?]", command)
        goal = sentences[0].strip()

        if not goal:
            goal = command

        return goal

    def _extract_constraints(self, command: str) -> List[str]:
        """
        Extract constraints from command.

        Examples:
        - Geographic: "越南", "东南亚", "Vietnam"
        - Industry: "食品", "包装", "food", "packaging"
        - Time: "本月", "Q1", "this month"
        """
        constraints = []

        # Geographic constraints
        geo_patterns = [
            r"([越南|泰国|印尼|马来西亚|菲律宾|新加坡|东南亚]+)",
            r"(Vietnam|Thailand|Indonesia|Malaysia|Philippines|Singapore|Southeast Asia)",
        ]
        for pattern in geo_patterns:
            matches = re.findall(pattern, command, re.IGNORECASE)
            constraints.extend(matches)

        # Industry/domain constraints
        industry_patterns = [
            r"([食品|饮料|包装|制造|零售|电商]+)",
            r"(food|beverage|packaging|manufacturing|retail|ecommerce)",
        ]
        for pattern in industry_patterns:
            matches = re.findall(pattern, command, re.IGNORECASE)
            constraints.extend(matches)

        # Time constraints
        time_patterns = [
            r"([本月|本季|本年|Q\d]+)",
            r"(this month|this quarter|this year)",
        ]
        for pattern in time_patterns:
            matches = re.findall(pattern, command, re.IGNORECASE)
            constraints.extend(matches)

        # Remove duplicates
        constraints = list(set(constraints))

        return constraints

    def _determine_priority(self, command: str) -> CommandPriority:
        """Determine command priority based on keywords."""
        command_lower = command.lower()

        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in command_lower for kw in keywords):
                return priority

        # Default priority
        return CommandPriority.NORMAL

    def _estimate_complexity(self, command: str) -> str:
        """Estimate task complexity based on keywords and length."""
        command_lower = command.lower()

        # Check for high complexity keywords
        if any(kw in command_lower for kw in self.COMPLEXITY_KEYWORDS["high"]):
            return "high"

        # Check for low complexity keywords
        if any(kw in command_lower for kw in self.COMPLEXITY_KEYWORDS["low"]):
            return "low"

        # Estimate by command length
        if len(command) > 100:
            return "high"
        elif len(command) < 30:
            return "low"

        return "medium"

    def _identify_required_agents(self, command: str) -> List[str]:
        """Identify which agent types are needed for this command."""
        command_lower = command.lower()
        required = []

        for agent_type, keywords in self.AGENT_KEYWORDS.items():
            if any(kw in command_lower for kw in keywords):
                required.append(agent_type)

        # Default: if no specific agent identified, use research + business
        if not required:
            required = ["research", "business"]

        return list(set(required))

    def _detect_language(self, command: str) -> str:
        """Detect command language (zh-CN or en-US)."""
        # Simple heuristic: check for Chinese characters
        if re.search(r"[\u4e00-\u9fff]", command):
            return "zh-CN"
        return "en-US"

    # ==================== P0-1: LLM 目标理解 ====================

    # LLM 目标解析提示词：输出结构化 JSON
    LLM_PARSE_PROMPT = """你是外贸企业的经营目标解析助手。从老板的自然语言目标中提取结构化经营要素。
只返回一个 JSON 对象，不要输出任何其他文字或 markdown 代码块标记。

JSON 字段说明：
- goal: 一句话目标摘要（不超过 50 字）
- kpi_name: 核心KPI名称（如"新增潜在客户数"、"成交金额"）；无法确定时为 null
- kpi_target: KPI 目标数值（数字）；无法确定时为 null
- kpi_unit: KPI 单位（如"个"、"美元"）；无法确定时为 null
- budget_total: 总预算（数字，美元）；老板未提预算时为 null
- time_start: 开始日期 "YYYY-MM-DD"；未提及为 null
- time_end: 截止日期 "YYYY-MM-DD"；老板说"30天内"等相对时限时按今天推算；未提及时为 null
- constraints: 约束条件数组（地域、行业、产品等）
- risk_boundaries: 风险边界数组（老板明确划定的边界，如"不超预算"、"不碰侵权产品"）；未提及时为空数组
- priority: "low" | "normal" | "high" | "critical"
- required_agents: 需要的 AI 员工类型数组，取值只能是 "research" "marketing" "sales" "business" "ceo_assistant"

老板目标：{command_text}"""

    async def parse_with_llm(self, command_text: str, context: Optional[Dict] = None) -> ParsedCommand:
        """
        LLM 目标理解：用真实 LLM 解析老板的自然语言目标。

        链路：Provider Gateway → LLM → 结构化 JSON → ParsedCommand。
        降级：无可用 Provider / LLM 失败 / 输出不可解析时，回退到
        规则解析（parse()），并在 metadata 中诚实标记：
          - metadata["parse_method"]: "llm" | "rule_based"
          - metadata["llm_error"]: 失败原因（仅降级时存在）
        """
        # 规则解析作为基线（无论 LLM 成败都保留可用字段）
        parsed = self.parse(command_text, context)
        parsed.metadata["parse_method"] = "rule_based"

        try:
            from .gateway import get_gateway

            gateway = get_gateway()
            providers = gateway.list_providers()
            if not providers:
                parsed.metadata["llm_error"] = "no_provider_configured"
                return parsed

            from uuid import UUID

            response = await gateway.complete(
                provider=providers[0],
                model_id="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": self.LLM_PARSE_PROMPT.format(command_text=command_text),
                    }
                ],
                trace_id=UUID(int=0),
                temperature=0.1,
                max_tokens=800,
            )

            data = self._extract_json_object(response.content)
            if not isinstance(data, dict):
                parsed.metadata["llm_error"] = "unparseable_response"
                return parsed

            self._merge_llm_extraction(parsed, data)
            parsed.metadata["parse_method"] = "llm"
            logger.info(
                "llm_goal_parse_succeeded",
                extra={"kpi": parsed.kpi_name, "budget": parsed.budget_total},
            )
        except Exception as e:  # noqa: BLE001 — LLM 失败必须降级而不是中断目标创建
            parsed.metadata["llm_error"] = str(e)[:200]
            logger.warning("llm_goal_parse_failed_fallback_to_rules", extra={"error": str(e)})

        return parsed

    def _extract_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 输出中提取 JSON 对象（容忍 markdown 代码块围栏）。"""
        if not text:
            return None
        cleaned = text.strip()
        # 去掉 ```json ... ``` 围栏
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if fence_match:
            cleaned = fence_match.group(1)
        else:
            # 裸 JSON：取第一个 { 到最后一个 }
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            cleaned = cleaned[start : end + 1]
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _merge_llm_extraction(self, parsed: ParsedCommand, data: Dict[str, Any]) -> None:
        """将 LLM 提取结果合并进 ParsedCommand（仅接受合法值）。"""
        if isinstance(data.get("goal"), str) and data["goal"].strip():
            parsed.goal = data["goal"].strip()

        if isinstance(data.get("kpi_name"), str) and data["kpi_name"].strip():
            parsed.kpi_name = data["kpi_name"].strip()
        kpi_target = data.get("kpi_target")
        if (
            isinstance(kpi_target, (int, float))
            and not isinstance(kpi_target, bool)
            and kpi_target >= 0
        ):
            parsed.kpi_target = float(kpi_target)
        if isinstance(data.get("kpi_unit"), str) and data["kpi_unit"].strip():
            parsed.kpi_unit = data["kpi_unit"].strip()

        budget = data.get("budget_total")
        if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0:
            parsed.budget_total = float(budget)

        for key in ("time_start", "time_end"):
            value = data.get(key)
            if isinstance(value, str):
                # 校验 ISO 日期格式
                if re.match(r"^\d{4}-\d{2}-\d{2}", value.strip()):
                    setattr(parsed, key, value.strip()[:10])

        if isinstance(data.get("constraints"), list):
            extra = [str(c) for c in data["constraints"] if c]
            parsed.constraints = list(set(parsed.constraints + extra))

        if isinstance(data.get("risk_boundaries"), list):
            parsed.risk_boundaries = [str(r) for r in data["risk_boundaries"] if r]

        if isinstance(data.get("priority"), str):
            try:
                parsed.priority = CommandPriority(data["priority"])
            except ValueError:
                pass  # 保留规则解析的优先级

        if isinstance(data.get("required_agents"), list):
            valid_agents = set(self.AGENT_KEYWORDS.keys())
            llm_agents = [a for a in data["required_agents"] if a in valid_agents]
            if llm_agents:
                parsed.required_agents = list(set(llm_agents))
