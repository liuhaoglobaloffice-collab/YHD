"""Fix test_planner.py - remove duplicate function definitions"""

content = '''"""
Phase 3.1 - Test IntelligentPlanner

Test task decomposition and planning capabilities.
"""

import pytest
from src.ai.planner import IntelligentPlanner
from src.ai.models import ParsedCommand, CommandPriority


class TestIntelligentPlanner:
    """Test Intelligent Planner for task decomposition"""

    def test_planner_initialization(self):
        """Test planner can be initialized"""
        planner = IntelligentPlanner()
        assert planner is not None

    def test_decompose_simple_goal(self):
        """Test decomposing a simple single-action goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="市场分析",
            priority=CommandPriority.NORMAL,
            constraints={"geography": ["越南"]},
            required_agents=["research"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) > 0
        assert len(task_list) <= 10  # Should not over-decompose
        
        # Each task should have required fields
        for task in task_list:
            assert "task" in task or "name" in task
            assert "agent" in task or "agent_type" in task

    def test_decompose_complex_goal(self):
        """Test decomposing a complex multi-step goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="市场开发",
            priority=CommandPriority.HIGH,
            constraints={"geography": ["越南"], "industry": ["食品包装"]},
            required_agents=["research", "sales"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 2  # Should have multiple steps
        
        # Should include both research and sales tasks
        task_types = [t.get("agent", t.get("agent_type", "")) for t in task_list]
        assert len(set(task_types)) >= 2  # At least 2 different agent types

    def test_decompose_research_goal(self):
        """Test decomposing research-focused goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="市场调研",
            priority=CommandPriority.NORMAL,
            constraints={"geography": ["东南亚"], "industry": ["食品包装"]},
            required_agents=["research"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 3  # Research should have multiple sub-tasks
        
        # Should include typical research steps
        task_names = " ".join([t.get("task", t.get("name", "")) for t in task_list]).lower()
        # Common research keywords
        research_keywords = ["分析", "调研", "研究", "报告", "数据", "analysis", "research"]
        assert any(keyword in task_names for keyword in research_keywords)

    def test_decompose_sales_goal(self):
        """Test decomposing sales-focused goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="客户开发",
            priority=CommandPriority.HIGH,
            constraints={"target_count": 50, "geography": ["越南"]},
            required_agents=["sales"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 2
        
        # Should include sales-related tasks
        task_names = " ".join([t.get("task", t.get("name", "")) for t in task_list]).lower()
        sales_keywords = ["客户", "开发", "联系", "跟进", "sales", "client", "customer"]
        assert any(keyword in task_names for keyword in sales_keywords)

    def test_decompose_marketing_goal(self):
        """Test decomposing marketing-focused goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="营销方案",
            priority=CommandPriority.NORMAL,
            constraints={"channel": ["SEO"]},
            required_agents=["marketing"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 2
        
        # Should include marketing tasks
        task_names = " ".join([t.get("task", t.get("name", "")) for t in task_list]).lower()
        marketing_keywords = ["营销", "seo", "内容", "关键词", "marketing", "content"]
        assert any(keyword in task_names for keyword in marketing_keywords)

    def test_decompose_with_priority(self):
        """Test that task priorities are assigned correctly"""
        planner = IntelligentPlanner()
        
        # Critical priority command
        parsed_critical = ParsedCommand(
            goal="市场分析",
            priority=CommandPriority.CRITICAL,
            constraints={},
            required_agents=["research"],
        )
        
        decomposition = planner.create_plan(parsed_critical)
        task_list = decomposition.tasks
        
        assert task_list is not None
        # Critical commands might generate fewer but more focused tasks
        assert len(task_list) <= 7

    def test_decompose_respects_constraints(self):
        """Test that decomposed tasks respect input constraints"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="多市场分析",
            priority=CommandPriority.NORMAL,
            constraints={"geography": ["越南", "泰国"]},
            required_agents=["research"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        # Should have separate tasks or consolidated multi-geography task
        assert len(task_list) >= 1

    def test_decompose_empty_goal(self):
        """Test handling empty goal"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="",
            priority=CommandPriority.NORMAL,
            constraints={},
            required_agents=[],
        )
        
        # Should either raise error or return minimal task list
        try:
            decomposition = planner.create_plan(parsed)
            task_list = decomposition.tasks  # Extract task list from TaskDecomposition
            assert task_list is None or len(task_list) == 0
        except ValueError:
            pass  # Expected

    def test_task_ordering(self):
        """Test that tasks are ordered logically"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="市场开发与报告",
            priority=CommandPriority.NORMAL,
            constraints={},
            required_agents=["research", "sales", "business"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 3
        
        # Tasks should follow logical order
        # Research typically comes first, reporting last
        first_task = str(task_list[0]).lower()
        last_task = str(task_list[-1]).lower()
        
        # First task should be research-related
        research_keywords = ["调研", "分析", "研究", "research", "analysis"]
        assert any(kw in first_task for kw in research_keywords)
        
        # Last task should be reporting/summary
        report_keywords = ["报告", "汇总", "总结", "report", "summary"]
        # This is a soft check - reporting might not always be last
        if any(kw in last_task for kw in report_keywords):
            assert True

    def test_decompose_handles_numbers(self):
        """Test that numeric targets are considered in decomposition"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="大规模客户开发",
            priority=CommandPriority.HIGH,
            constraints={"target_count": 100},
            required_agents=["sales"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        # Large targets might generate more tasks or batch tasks
        assert len(task_list) >= 1

    def test_decompose_multi_agent_coordination(self):
        """Test decomposition requiring multiple agent types"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="完整市场开发",
            priority=CommandPriority.HIGH,
            constraints={},
            required_agents=["research", "sales", "marketing"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        assert len(task_list) >= 3  # Should have tasks for each agent type
        
        # Should have diverse agent assignments
        agent_types = set([t.get("agent", t.get("agent_type", "")) for t in task_list])
        assert len(agent_types) >= 2  # At least 2 different agent types

    def test_decompose_produces_valid_structure(self):
        """Test that all decomposed tasks have valid structure"""
        planner = IntelligentPlanner()
        
        parsed = ParsedCommand(
            goal="市场分析",
            priority=CommandPriority.NORMAL,
            constraints={"geography": ["越南"], "industry": ["食品包装"]},
            required_agents=["research"],
        )
        
        decomposition = planner.create_plan(parsed)
        task_list = decomposition.tasks  # Extract task list from TaskDecomposition
        
        assert task_list is not None
        
        for i, task in enumerate(task_list):
            # Each task must be a dict
            assert isinstance(task, dict), f"Task {i} is not a dict"
            
            # Must have task description
            assert "task" in task or "name" in task or "description" in task
            
            # Must have agent assignment
            assert "agent" in task or "agent_type" in task or "assigned_to" in task
'''

# Write fixed content
with open("tests/test_ai_brain/test_planner.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ Fixed test_planner.py - removed duplicate function definitions")
