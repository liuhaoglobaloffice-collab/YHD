"""
CEO Command Processor - Phase 3.1 AI Brain Core

Processes natural language commands from CEO and converts them to
structured ParsedCommand for planning.
"""

import logging
import re
from typing import Dict, List, Optional

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
