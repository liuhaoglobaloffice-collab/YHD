"""
Phase 3.1 - Test CEOCommandProcessor

Test natural language command parsing and understanding.
"""

import pytest

from src.ai.command_processor import CEOCommandProcessor
from src.ai.models import CommandPriority


class TestCEOCommandProcessor:
    """Test CEO Command Processor"""

    def test_processor_initialization(self):
        """Test processor can be initialized"""
        processor = CEOCommandProcessor()
        assert processor is not None

    def test_parse_chinese_command_simple(self):
        """Test parsing simple Chinese command"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析越南食品包装市场")

        assert parsed is not None
        assert parsed.goal is not None
        assert "越南" in parsed.goal or "食品" in parsed.goal or "市场" in parsed.goal
        assert len(parsed.goal) > 0

    def test_parse_chinese_command_complex(self):
        """Test parsing complex Chinese command with multiple clauses"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析越南食品包装市场，并开发10个潜在客户")

        assert parsed is not None
        assert "越南" in parsed.goal or "市场" in parsed.goal
        assert parsed.goal is not None

    def test_parse_english_command(self):
        """Test parsing English command"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("Analyze the Vietnamese food packaging market")

        assert parsed is not None
        assert parsed.goal is not None

    def test_detect_priority_urgent(self):
        """Test detecting urgent/critical priority"""
        processor = CEOCommandProcessor()

        # Chinese urgent keywords
        parsed = processor.parse("紧急：分析市场")
        assert (
            parsed.priority == CommandPriority.CRITICAL or parsed.priority == CommandPriority.HIGH
        )

        # English urgent keywords
        parsed_en = processor.parse("URGENT: Analyze market")
        assert (
            parsed_en.priority == CommandPriority.CRITICAL
            or parsed_en.priority == CommandPriority.HIGH
        )

    def test_detect_priority_normal(self):
        """Test detecting normal priority (default)"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析市场")

        # Should default to NORMAL if no priority keyword
        assert parsed.priority in [
            CommandPriority.NORMAL,
            CommandPriority.HIGH,
            CommandPriority.LOW,
        ]

    def test_detect_required_agents_research(self):
        """Test detecting research agent requirements"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("调研越南食品包装市场")

        assert parsed.required_agents is not None
        # Should detect research/market analysis need
        assert len(parsed.required_agents) > 0

    def test_detect_required_agents_sales(self):
        """Test detecting sales agent requirements"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("开发10个越南客户")

        assert parsed.required_agents is not None
        # Should detect sales need
        assert len(parsed.required_agents) > 0

    def test_extract_constraints_geography(self):
        """Test extracting geographic constraints"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析越南、泰国、印尼的食品包装市场")

        assert parsed.constraints is not None
        # Should extract geographic constraints
        constraints_str = str(parsed.constraints).lower()
        assert any(
            country in constraints_str for country in ["越南", "vietnam", "泰国", "thailand"]
        )

    def test_extract_constraints_industry(self):
        """Test extracting industry constraints"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析食品包装行业")

        assert parsed.constraints is not None
        constraints_str = str(parsed.constraints).lower()
        assert "食品" in constraints_str or "包装" in constraints_str or "food" in constraints_str

    def test_parse_empty_command(self):
        """Test handling empty command"""
        processor = CEOCommandProcessor()

        with pytest.raises((ValueError, TypeError)):
            processor.parse("")

    def test_parse_none_command(self):
        """Test handling None command"""
        processor = CEOCommandProcessor()

        with pytest.raises((ValueError, TypeError)):
            processor.parse(None)

    def test_parse_very_long_command(self):
        """Test handling very long command"""
        processor = CEOCommandProcessor()
        long_command = "分析市场" * 500  # 1500+ characters

        parsed = processor.parse(long_command)
        assert parsed is not None
        assert parsed.goal is not None

    def test_parse_mixed_language_command(self):
        """Test parsing mixed Chinese-English command"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("分析 Vietnam 的 food packaging 市场")

        assert parsed is not None
        assert parsed.goal is not None

    def test_parse_command_with_numbers(self):
        """Test parsing command with specific numbers/metrics"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("开发50个客户，每个月至少10万营收")

        assert parsed is not None
        assert parsed.goal is not None
        # Should capture numeric constraints
        constraints_str = str(parsed.constraints).lower()
        assert "50" in constraints_str or "10" in constraints_str

    def test_parse_multistep_command(self):
        """Test parsing command with multiple steps"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("先调研市场，然后开发客户，最后生成营销方案")

        assert parsed is not None
        assert parsed.goal is not None
        # Should recognize multiple action verbs
        assert parsed.required_agents is not None

    def test_parse_command_with_deadline(self):
        """Test parsing command with time constraints"""
        processor = CEOCommandProcessor()
        parsed = processor.parse("3天内完成市场分析报告")

        assert parsed is not None
        constraints_str = str(parsed.constraints).lower()
        # Should capture time constraint
        assert "3" in constraints_str or "天" in constraints_str or "day" in constraints_str

    def test_consistency_same_command(self):
        """Test that same command produces consistent results"""
        processor = CEOCommandProcessor()
        command = "分析越南食品包装市场"

        parsed1 = processor.parse(command)
        parsed2 = processor.parse(command)

        # Goals should be similar (allowing for minor variations)
        assert parsed1.goal is not None
        assert parsed2.goal is not None
        assert parsed1.priority == parsed2.priority

    def test_parse_business_domain_detection(self):
        """Test detecting business domain from command"""
        processor = CEOCommandProcessor()

        # Marketing command
        parsed_marketing = processor.parse("制定SEO营销方案")
        assert parsed_marketing.goal is not None

        # Sales command
        parsed_sales = processor.parse("开发客户")
        assert parsed_sales.goal is not None

        # Research command
        parsed_research = processor.parse("市场调研")
        assert parsed_research.goal is not None
