"""
S5 AI 员工市场 + 元学习 + 自我进化（Market & Evolution）

AI 员工市场（内部/外部模板、技能包）、
鎏灏元学习（吸收团队知识）、自我进化（优化方案）。
"""

from .growth import MetaLearningService, SelfEvolutionService
from .market import MarketService
from .models import (
    EmployeeTemplate,
    EvolutionProposal,
    MetaKnowledge,
    ProposalStatus,
    SkillPack,
    TemplateCategory,
)

__all__ = [
    "EmployeeTemplate",
    "EvolutionProposal",
    "MarketService",
    "MetaKnowledge",
    "MetaLearningService",
    "ProposalStatus",
    "SelfEvolutionService",
    "SkillPack",
    "TemplateCategory",
]