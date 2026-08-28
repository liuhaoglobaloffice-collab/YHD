"""
主/子账号数据可见范围助手.

数据权限范围（data_scope）控制逻辑：
- OWNER 主账号：始终可见 tenant 内全部数据
- SUB 子账号：根据 data_scope 字段限制可见范围
  - "self"       → 仅本人创建的数据（owner_user_id = 自己）
  - "department" → 本部门数据（department_id = 自己部门）
  - "all"        → 全公司数据（tenant_id 内，无用户级过滤）

使用方式：
  scope = DataScopeFilter(user)
  query = scope.apply_to_query(query, Lead, owner_field="owner_user_id")
  或
  user_ids = scope.visible_user_ids()  # 返回可用的 owner_user_id 集合
"""

from typing import Optional, Set

from sqlalchemy import ColumnElement, Select, and_
from sqlalchemy.sql.elements import BinaryExpression

from src.identity.models import AccountType, User


class DataScopeFilter:
    """数据权限范围过滤器，封装了 data_scope 的检查逻辑。"""

    def __init__(self, user: Optional[User]):
        self._user = user

    # ─── 判断逻辑 ───────────────────────────────────────────

    def is_owner(self) -> bool:
        """当前用户是否是主账号。"""
        return self._user is not None and (
            self._user.account_type == AccountType.OWNER
            or getattr(self._user, "is_superuser", False)
        )

    def effective_scope(self) -> str:
        """返回实际生效的数据范围。

        主账号始终为 "all"，子账号按配置返回。
        """
        if self.is_owner():
            return "all"
        if self._user is None:
            return "self"
        return self._user.data_scope or "self"

    # ─── 可见用户 ID 集合（兼容旧版 service 接口） ───────────

    def visible_user_ids(self) -> Set[int]:
        """
        返回可见的数据归属用户 ID 集合。

        注意：此方法只适用于按 owner_user_id 过滤的场景。
        对于 "all" 范围，返回空集表示不过滤（调用方应自行判断）。
        """
        if not self._user:
            return set()

        scope = self.effective_scope()

        if scope == "all":
            # 全公司数据：不过滤 owner_user_id
            return set()

        if scope == "department" and self._user.department_id:
            # 本部门数据：返回空集，调用方应使用 apply_department_filter
            # （因为部门过滤不能只靠 user_id 集合，需要 SQL 层 join 或 department_id 过滤）
            return set()

        # "self" 或 fallback
        return {self._user.id}

    # ─── SQL 查询构建器 ────────────────────────────────────

    def apply_to_query(
        self,
        query: Select,
        model: type,
        *,
        owner_field: str = "owner_user_id",
        tenant_field: str = "tenant_id",
        user_id_field: str = "created_by",
    ) -> Select:
        """
        在 SQLAlchemy Select 查询上应用数据范围过滤。

        参数：
            query       - 原始 Select 查询
            model       - ORM 模型类
            owner_field - 数据归属用户字段名（默认 "owner_user_id"）
            tenant_field - 租户字段名（默认 "tenant_id"）
            user_id_field - 创建者字段名（默认 "created_by"）

        返回：
            添加了 WHERE 条件的查询
        """
        if not self._user:
            return query

        scope = self.effective_scope()

        # TENANT 隔离始终生效
        tenant_col = getattr(model, tenant_field, None)
        if tenant_col is not None and self._user.tenant_id:
            query = query.where(tenant_col == self._user.tenant_id)

        # 主账号：tenant 隔离就够了，不需要额外用户级过滤
        if self.is_owner():
            return query

        # 子账号：根据 data_scope 添加过滤
        if scope == "self":
            # 仅本人数据：owner_user_id = 自己
            owner_col = getattr(model, owner_field, None)
            if owner_col is not None:
                query = query.where(owner_col == self._user.id)
            else:
                # fallback: created_by = 自己
                who_col = getattr(model, user_id_field, None)
                if who_col is not None:
                    query = query.where(who_col == self._user.id)

        elif scope == "department":
            # 本部门数据：department_id = 自己部门
            dept_col = getattr(model, "department_id", None)
            if dept_col is not None and self._user.department_id:
                query = query.where(dept_col == self._user.department_id)
            else:
                # 没有 department_id 字段或用户没有部门，回退到仅本人
                owner_col = getattr(model, owner_field, None)
                if owner_col is not None:
                    query = query.where(owner_col == self._user.id)
                else:
                    who_col = getattr(model, user_id_field, None)
                    if who_col is not None:
                        query = query.where(who_col == self._user.id)

        # scope == "all"：仅 tenant 隔离，不过滤用户

        return query

    def apply_to_statement(
        self,
        stmt: Select,
        model: type,
        *,
        owner_field: str = "owner_user_id",
        tenant_field: str = "tenant_id",
    ) -> Select:
        """
        apply_to_query 的别名，与 accounts.py 中的命名风格一致。
        """
        return self.apply_to_query(
            stmt,
            model,
            owner_field=owner_field,
            tenant_field=tenant_field,
        )

    # ─── 可见性检查（用于单条记录详情） ────────────────────

    def can_access_record(self, record_user_id: Optional[int] = None, **kwargs) -> bool:
        """
        检查当前用户是否有权访问某条记录。

        可传入 record_user_id（owner_user_id）或
        使用 kwargs 传入更多字段（如 department_id, tenant_id）。

        对于主账号始终返回 True（注意：调用方应确保 tenant_id 匹配）。
        """
        if self.is_owner():
            return True

        scope = self.effective_scope()

        if scope == "all":
            return True

        if scope == "self":
            return record_user_id == self._user.id

        if scope == "department":
            dept_id = kwargs.get("department_id")
            if dept_id is not None and self._user.department_id:
                return dept_id == self._user.department_id
            # 没有 department_id 信息，回退到 owner_user_id 检查
            return record_user_id == self._user.id

        return True

    # ─── 兼容旧版函数签名 ──────────────────────────────────

    @classmethod
    def get_visible_user_ids(cls, user: Optional[User]) -> Set[int]:
        """兼容旧版 visible_user_ids 函数。"""
        return cls(user).visible_user_ids()


# ─── 旧版函数（保持向后兼容） ─────────────────────────────


def visible_user_ids(user: Optional[User]) -> Set[int]:
    """
    旧版：返回该用户可见的数据归属用户 ID 集合。

    注意：对于 data_scope = "all" 的情况，此函数返回空集，
    调用方应该在 SQL 中改用 DataScopeFilter.apply_to_query()。
    """
    return DataScopeFilter.get_visible_user_ids(user)


def scope_label(user: Optional[User]) -> str:
    """可见范围标识（owner/sub），供接口返回。"""
    if user and user.account_type == AccountType.SUB:
        return "sub"
    return "owner"