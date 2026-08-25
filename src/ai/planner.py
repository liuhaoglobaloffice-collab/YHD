"""
Intelligent Planner - Phase 3.1 AI Brain Core

Decomposes high-level goals into executable task plans.
"""

import logging
from typing import Dict, List
from uuid import uuid4

from .models import CommandPriority, ParsedCommand, TaskDecomposition

logger = logging.getLogger(__name__)


class IntelligentPlanner:
    """
    Decomposes goals into executable task plans.

    Responsibilities:
    - Break down goals into tasks
    - Determine execution order
    - Assign task types to agents
    - Estimate duration
    """

    # Task templates for common goals (Phase 3.1 heuristics)
    TASK_TEMPLATES = {
        "market_analysis": [
            {"name": "市场调研", "agent": "research", "duration": 30},
            {"name": "竞争分析", "agent": "research", "duration": 20},
            {"name": "客户画像", "agent": "sales", "duration": 20},
            {"name": "市场规模评估", "agent": "business", "duration": 15},
            {"name": "汇总报告", "agent": "ceo_assistant", "duration": 10},
        ],
        "seo_optimization": [
            {"name": "关键词研究", "agent": "marketing", "duration": 20},
            {"name": "内容优化", "agent": "marketing", "duration": 30},
            {"name": "链接建设", "agent": "marketing", "duration": 25},
            {"name": "效果监测", "agent": "marketing", "duration": 15},
        ],
        "customer_development": [
            {"name": "目标客户定位", "agent": "sales", "duration": 15},
            {"name": "客户资料收集", "agent": "sales", "duration": 30},
            {"name": "初步联系", "agent": "sales", "duration": 45},
            {"name": "跟进记录", "agent": "sales", "duration": 20},
        ],
        "business_operation": [
            {"name": "流程梳理", "agent": "business", "duration": 20},
            {"name": "数据整理", "agent": "business", "duration": 30},
            {"name": "任务执行", "agent": "business", "duration": 40},
            {"name": "结果汇总", "agent": "business", "duration": 15},
        ],
    }

    def __init__(self):
        logger.info("IntelligentPlanner initialized")

    def create_plan(self, parsed_command: ParsedCommand) -> TaskDecomposition:
        """
        Create execution plan from parsed command.

        Args:
            parsed_command: Parsed CEO command

        Returns:
            TaskDecomposition with task list and execution plan
        """
        # Select template based on goal and required agents
        template_key = self._select_template(parsed_command)

        # Generate tasks from template
        tasks = self._generate_tasks(template_key, parsed_command)

        # Determine execution order
        execution_order = self._determine_execution_order(tasks, parsed_command.priority)

        # Build dependencies
        dependencies = self._build_dependencies(tasks, execution_order)

        # Estimate total duration
        duration = self._estimate_duration(tasks, parsed_command.estimated_complexity)

        plan = TaskDecomposition(
            goal=parsed_command.goal,
            tasks=tasks,
            execution_order=execution_order,
            estimated_duration_minutes=duration,
            dependencies=dependencies,
            metadata={
                "template": template_key,
                "constraints": parsed_command.constraints,
                "priority": parsed_command.priority.value,
            },
        )

        logger.info(
            f"Created task plan: {len(tasks)} tasks, "
            f"order={execution_order}, duration={duration}min"
        )

        return plan

    def _select_template(self, parsed: ParsedCommand) -> str:
        """
        Select appropriate task template based on goal and agents.

        Phase 3.1: Simple keyword matching.
        Future: LLM-based template selection.
        """
        goal_lower = parsed.goal.lower()
        agents = parsed.required_agents

        # Market analysis keywords
        if any(
            kw in goal_lower for kw in ["市场", "分析", "调研", "market", "analysis", "research"]
        ):
            return "market_analysis"

        # SEO/Marketing keywords
        if any(
            kw in goal_lower for kw in ["SEO", "营销", "推广", "优化", "marketing", "optimization"]
        ):
            return "seo_optimization"

        # Sales/Customer keywords
        if any(kw in goal_lower for kw in ["客户", "销售", "开发", "customer", "sales", "lead"]):
            return "customer_development"

        # Business/Operation keywords
        if any(
            kw in goal_lower for kw in ["业务", "运营", "管理", "business", "operation", "manage"]
        ):
            return "business_operation"

        # Default: market analysis (most general)
        if "research" in agents:
            return "market_analysis"
        elif "sales" in agents:
            return "customer_development"
        elif "marketing" in agents:
            return "seo_optimization"

        return "business_operation"

    def _generate_tasks(self, template_key: str, parsed: ParsedCommand) -> List[Dict]:
        """
        Generate task list from template, customized for goal.
        """
        template = self.TASK_TEMPLATES.get(template_key, self.TASK_TEMPLATES["business_operation"])

        tasks = []
        for idx, task_template in enumerate(template):
            task = {
                "task_id": str(uuid4()),
                "order": idx + 1,
                "name": task_template["name"],
                "description": f"{parsed.goal} - {task_template['name']}",
                "agent_type": task_template["agent"],
                "estimated_duration_minutes": task_template["duration"],
                "constraints": parsed.constraints,
                "metadata": {
                    "goal": parsed.goal,
                    "template": template_key,
                },
            }
            tasks.append(task)

        return tasks

    def _determine_execution_order(self, tasks: List[Dict], priority: CommandPriority) -> str:
        """
        Determine whether tasks should run sequentially or in parallel.

        Rules:
        - CRITICAL/HIGH: Sequential (ensure quality)
        - NORMAL/LOW: Hybrid (balance speed and quality)
        - Single agent: Sequential
        - Multi-agent: Parallel where possible
        """
        if priority in [CommandPriority.CRITICAL, CommandPriority.HIGH]:
            return "sequential"

        # Check if tasks can run in parallel (different agents)
        agents = set(task["agent_type"] for task in tasks)
        if len(agents) > 1 and len(tasks) > 2:
            return "hybrid"

        return "sequential"

    def _build_dependencies(self, tasks: List[Dict], execution_order: str) -> Dict[str, List[str]]:
        """
        Build task dependency graph.

        Sequential: Each task depends on previous
        Parallel: No dependencies
        Hybrid: Group by agent, sequential within group
        """
        dependencies = {}

        if execution_order == "sequential":
            # Each task depends on previous task
            for i in range(1, len(tasks)):
                task_id = tasks[i]["task_id"]
                prev_id = tasks[i - 1]["task_id"]
                dependencies[task_id] = [prev_id]

        elif execution_order == "hybrid":
            # Group tasks by agent, dependencies within same agent
            agent_groups: Dict[str, List[Dict]] = {}
            for task in tasks:
                agent = task["agent_type"]
                if agent not in agent_groups:
                    agent_groups[agent] = []
                agent_groups[agent].append(task)

            # Sequential within each agent group
            for agent_tasks in agent_groups.values():
                for i in range(1, len(agent_tasks)):
                    task_id = agent_tasks[i]["task_id"]
                    prev_id = agent_tasks[i - 1]["task_id"]
                    dependencies[task_id] = [prev_id]

        # Parallel: no dependencies needed

        return dependencies

    def _estimate_duration(self, tasks: List[Dict], complexity: str) -> int:
        """
        Estimate total execution time in minutes.
        """
        base_duration = sum(task.get("estimated_duration_minutes", 20) for task in tasks)

        # Adjust for complexity
        multiplier = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.5,
        }.get(complexity, 1.0)

        return int(base_duration * multiplier)
