"""
S5 AI 员工市场 + 元学习 + 自我进化 - 数据模型

定义员工市场模板（EmployeeTemplate）、技能包（SkillPack）、
元学习知识（MetaKnowledge）、进化方案（EvolutionProposal）。
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)

from src.database.base import Base


class TemplateCategory(str, Enum):
    """模板分类"""

    INTERNAL = "internal"  # 内部模板（系统预置）
    EXTERNAL = "external"  # 外部模板（市场/第三方）


class ProposalStatus(str, Enum):
    """进化方案状态"""

    DRAFT = "draft"
    APPLIED = "applied"
    REJECTED = "rejected"


class EmployeeTemplate(Base):
    """AI 员工市场模板"""

    __tablename__ = "employee_templates"

    id = Column(Integer, primary_key=True, index=True, comment="模板ID")

    # 基本信息
    name = Column(String(255), nullable=False, comment="名称")
    department = Column(String(100), nullable=False, default="operations", comment="部门")
    position = Column(String(100), nullable=False, default="task_manager", comment="职位")
    description = Column(Text, nullable=True, comment="描述")
    agent_type = Column(String(50), nullable=True, comment="Agent 类型")

    # 市场信息
    category = Column(
        SQLEnum(TemplateCategory), nullable=False, default=TemplateCategory.INTERNAL, index=True, comment="分类"
    )
    author = Column(String(255), nullable=True, comment="作者/来源")
    version = Column(String(20), nullable=False, default="1.0", comment="版本")
    price = Column(Integer, nullable=False, default=0, comment="价格（积分/分）")
    rating = Column(Integer, nullable=False, default=0, comment="评分 0-5")
    installs = Column(Integer, nullable=False, default=0, comment="安装次数")

    # 模板内容
    skill_ids = Column(JSON, nullable=True, comment="关联技能包 ID 列表")
    system_prompt = Column(Text, nullable=True, comment="系统提示词模板")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    # 归属
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<EmployeeTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"


class SkillPack(Base):
    """AI 员工技能包"""

    __tablename__ = "skill_packs"

    id = Column(Integer, primary_key=True, index=True, comment="技能包ID")

    name = Column(String(255), nullable=False, comment="技能包名称")
    code = Column(String(100), unique=True, nullable=False, index=True, comment="技能编码")
    description = Column(Text, nullable=True, comment="描述")
    category = Column(String(100), nullable=False, default="general", index=True, comment="分类")

    # 技能内容
    capabilities = Column(JSON, nullable=True, comment="能力列表")
    prompt_fragments = Column(JSON, nullable=True, comment="提示词片段")
    tools = Column(JSON, nullable=True, comment="工具列表")

    is_system = Column(Boolean, nullable=False, default=False, comment="是否系统内置")
    version = Column(String(20), nullable=False, default="1.0", comment="版本")
    meta = Column(JSON, nullable=True, comment="扩展信息")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="更新时间",
    )

    def __repr__(self) -> str:
        return f"<SkillPack(id={self.id}, name='{self.name}', code='{self.code}')>"


class MetaKnowledge(Base):
    """鎏灏元学习知识（吸收其他 AI 员工信息增长而来）"""

    __tablename__ = "meta_knowledge"

    id = Column(Integer, primary_key=True, index=True, comment="知识ID")

    # 来源
    source_employee_id = Column(Integer, nullable=True, index=True, comment="来源员工ID")
    source_employee_name = Column(String(255), nullable=True, comment="来源员工名称")
    source_type = Column(String(50), nullable=False, comment="来源类型（employee/skill/template）")

    # 知识内容
    title = Column(String(500), nullable=False, comment="知识标题")
    summary = Column(Text, nullable=True, comment="知识摘要")
    knowledge = Column(Text, nullable=True, comment="完整知识内容")
    tags = Column(JSON, nullable=True, comment="标签")

    # 生成信息
    method = Column(String(20), nullable=False, default="ai", comment="生成方式（ai/mock）")
    created_by = Column(Integer, nullable=True, comment="触发人ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<MetaKnowledge(id={self.id}, title='{self.title}')>"


class EvolutionProposal(Base):
    """鎏灏自我进化方案（评估系统并给出优化建议）"""

    __tablename__ = "evolution_proposals"

    id = Column(Integer, primary_key=True, index=True, comment="方案ID")

    title = Column(String(500), nullable=False, comment="方案标题")
    category = Column(String(100), nullable=False, default="system", comment="类别（system/flow/market/knowledge）")

    # 内容
    analysis = Column(Text, nullable=True, comment="系统评估分析")
    improvements = Column(JSON, nullable=True, comment="改进建议（数组）")
    risks = Column(JSON, nullable=True, comment="风险（数组）")
    action_plan = Column(JSON, nullable=True, comment="行动计划（数组）")
    summary = Column(Text, nullable=True, comment="方案摘要")
    full_text = Column(Text, nullable=True, comment="完整方案正文")

    # 状态
    status = Column(
        SQLEnum(ProposalStatus), nullable=False, default=ProposalStatus.DRAFT, index=True, comment="状态"
    )

    # 生成信息
    method = Column(String(20), nullable=False, default="ai", comment="生成方式（ai/mock）")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True, comment="创建时间"
    )
    applied_at = Column(DateTime(timezone=True), nullable=True, comment="采纳时间")

    def __repr__(self) -> str:
        return f"<EvolutionProposal(id={self.id}, title='{self.title}', status='{self.status}')>"