"""
Unit tests for DataScopeFilter (data visibility filtering).

Covers:
- DataScopeFilter.is_owner()
- DataScopeFilter.effective_scope()
- DataScopeFilter.visible_user_ids() (instance method, compatibility)
- DataScopeFilter.can_access_record() (single record check)
- DataScopeFilter.apply_to_query() (SQL query filtering)
- All three data scopes: "self" / "department" / "all"
- Backward compatibility with existing visible_user_ids()
- Edge cases: None user, missing columns, no department
"""

from sqlalchemy import Column, Integer, select
from sqlalchemy.orm import declarative_base

from src.identity.models import AccountType
from src.identity.visibility import DataScopeFilter, visible_user_ids, scope_label


# ============================================================
# Test Helpers
# ============================================================

def create_test_user(**kwargs):
    """Create a mock User object for testing."""
    defaults = {
        "id": 123,
        "account_type": AccountType.OWNER,
        "tenant_id": 42,
        "department_id": 10,
        "data_scope": "self",
        "permissions_config": None,
        "is_active": True,
    }
    defaults.update(kwargs)
    return type("MockUser", (), defaults)()


# Proper ORM model for column-aware SQL compilation
DeclBase = declarative_base()


class MockLead(DeclBase):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer)
    owner_user_id = Column(Integer)
    department_id = Column(Integer)
    created_by = Column(Integer)


class MockSupplier(DeclBase):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer)
    created_by = Column(Integer)


def _count_conditions(query) -> int:
    """Count the number of where clauses conditions in the query."""
    # For testing purposes, we can check the compiled SQL string for WHERE clauses
    # and count how many AND-separated conditions there are
    compiled = query.compile(compile_kwargs={"literal_binds": False})
    sql_str = str(compiled)

    if "WHERE" not in sql_str:
        return 0

    parts = sql_str.split("WHERE", 1)[1]
    # Each equality comparison has one parameter
    # Count the number of : (parameter placeholders)
    return sql_str.count(':')


def _has_where_clause(query) -> bool:
    """Check if the query has a WHERE clause."""
    compiled = query.compile(compile_kwargs={"literal_binds": False})
    return "WHERE" in str(compiled)


# ============================================================
# 1. is_owner and effective_scope tests
# ============================================================

class TestDataScopeFilterBasics:
    """基础测试：判断逻辑"""

    def test_owner_account_is_owner(self):
        """主账号应该被识别为 owner"""
        user = create_test_user(id=1, account_type=AccountType.OWNER)
        assert DataScopeFilter(user).is_owner() is True

    def test_sub_account_is_not_owner(self):
        """子账号不是 owner"""
        user = create_test_user(id=1, account_type=AccountType.SUB)
        assert DataScopeFilter(user).is_owner() is False

    def test_owner_effective_scope_is_always_all(self):
        """主账号永远返回 all"""
        user = create_test_user(id=1, account_type=AccountType.OWNER, data_scope="self")
        assert DataScopeFilter(user).effective_scope() == "all"

    def test_sub_account_uses_configured_scope(self):
        """子账号使用配置的 scope"""
        user = create_test_user(id=1, account_type=AccountType.SUB, data_scope="all")
        assert DataScopeFilter(user).effective_scope() == "all"

        user2 = create_test_user(id=1, account_type=AccountType.SUB, data_scope="department")
        assert DataScopeFilter(user2).effective_scope() == "department"

        user3 = create_test_user(id=1, account_type=AccountType.SUB, data_scope="self")
        assert DataScopeFilter(user3).effective_scope() == "self"

    def test_sub_account_defaults_to_self_when_none(self):
        """子账号没有配置 scope 时默认 self"""
        user = create_test_user(id=1, account_type=AccountType.SUB, data_scope=None)
        assert DataScopeFilter(user).effective_scope() == "self"

    def test_none_user_effective_scope_is_self(self):
        """user 为 None 时默认 self"""
        assert DataScopeFilter(None).effective_scope() == "self"


# ============================================================
# 2. visible_user_ids compatibility tests
# ============================================================

class TestVisibleUserIdsCompatibility:
    """visible_user_ids() 兼容性测试"""

    def test_owner_returns_empty_set(self):
        """主账号返回空集（不过滤）"""
        user = create_test_user(id=123, account_type=AccountType.OWNER)
        assert DataScopeFilter(user).visible_user_ids() == set()

    def test_sub_self_scope_returns_just_itself(self):
        """self 范围返回 {user_id}"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self")
        assert DataScopeFilter(user).visible_user_ids() == {123}

    def test_sub_all_scope_returns_empty_set(self):
        """all 范围返回空集（不过滤）"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="all")
        assert DataScopeFilter(user).visible_user_ids() == set()

    def test_sub_department_scope_with_dept_returns_empty_set(self):
        """department 范围（且有部门ID）返回空集"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department", department_id=10)
        assert DataScopeFilter(user).visible_user_ids() == set()

    def test_sub_department_scope_without_dept_falls_back_to_self(self):
        """department 范围但没有部门ID → 回退到 self，返回 {user_id}"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department", department_id=None)
        assert DataScopeFilter(user).visible_user_ids() == {123}

    def test_module_level_function_compatibility(self):
        """模块级旧函数兼容性"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self")
        assert visible_user_ids(user) == {123}

    def test_classmethod_get_visible_user_ids(self):
        """类方法 get_visible_user_ids 兼容性"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self")
        assert DataScopeFilter.get_visible_user_ids(user) == {123}


# ============================================================
# 3. can_access_record single record tests
# ============================================================

class TestCanAccessRecord:
    """单条记录可见性检查"""

    def test_owner_can_access_any_record(self):
        """主账号可以访问任何记录"""
        user = create_test_user(id=1, account_type=AccountType.OWNER)
        assert DataScopeFilter(user).can_access_record(record_user_id=999) is True

    def test_sub_self_scope_can_access_own_record(self):
        """self 范围的子账号可以访问自己创建的记录"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self")
        assert DataScopeFilter(user).can_access_record(record_user_id=123) is True

    def test_sub_self_scope_cannot_access_other_record(self):
        """self 范围的子账号不能访问别人创建的记录"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self")
        assert DataScopeFilter(user).can_access_record(record_user_id=456) is False

    def test_sub_all_scope_can_access_any_record(self):
        """all 范围的子账号可以访问任何记录"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="all")
        assert DataScopeFilter(user).can_access_record(record_user_id=456) is True

    def test_sub_department_scope_same_department_yes(self):
        """department 范围，同部门 → 可访问"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department", department_id=10)
        assert DataScopeFilter(user).can_access_record(record_user_id=456, department_id=10) is True

    def test_sub_department_scope_different_department_no(self):
        """department 范围，不同部门 → 不可访问"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department", department_id=10)
        assert DataScopeFilter(user).can_access_record(record_user_id=456, department_id=11) is False

    def test_sub_department_no_dept_id_falls_back_to_owner_check(self):
        """department 范围但记录没有 department_id → 回退到 owner_user_id 检查"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department", department_id=10)
        assert DataScopeFilter(user).can_access_record(record_user_id=123) is True
        assert DataScopeFilter(user).can_access_record(record_user_id=456) is False


# ============================================================
# 4. apply_to_query SQL tests
# ============================================================

class TestApplyToQuery:
    """SQL 查询应用过滤"""

    def test_no_user_returns_original_query(self):
        """user 为 None 不添加过滤"""
        query = select(MockLead.id)
        q1 = query.compile(compile_kwargs={"literal_binds": False})
        q2 = DataScopeFilter(None).apply_to_query(query, MockLead).compile(compile_kwargs={"literal_binds": False})
        assert str(q1) == str(q2)

    def test_owner_adds_tenant_filter_only(self):
        """主账号只加 tenant 过滤"""
        user = create_test_user(id=1, account_type=AccountType.OWNER, tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 1 param: tenant_id
        assert _count_conditions(result) == 1

    def test_sub_self_scope_adds_owner_user_id_filter(self):
        """子账号 self 范围添加 owner_user_id + tenant_id"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self", tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 2 params: tenant_id + owner_user_id
        assert _count_conditions(result) == 2

    def test_sub_self_falls_back_to_created_by_when_no_owner_field(self):
        """模型没有 owner_user_id → 回退到 created_by"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self", tenant_id=42)
        query = select(MockSupplier.id)
        result = DataScopeFilter(user).apply_to_query(query, MockSupplier)
        # 2 params: tenant_id + created_by
        assert _count_conditions(result) == 2

    def test_sub_department_adds_department_id_filter(self):
        """子账号 department 范围添加 department_id + tenant_id"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department",
                              department_id=10, tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 2 params: tenant_id + department_id
        assert _count_conditions(result) == 2

    def test_sub_department_no_department_id_on_user_falls_back_to_owner(self):
        """用户没有 department_id → 回退到 owner_user_id"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department",
                              department_id=None, tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 2 params: tenant_id + owner_user_id
        assert _count_conditions(result) == 2

    def test_sub_all_scope_adds_only_tenant_filter(self):
        """all 范围只添加 tenant 过滤"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="all", tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 1 param: tenant_id only
        assert _count_conditions(result) == 1

    def test_owner_no_tenant_id_skips_tenant_filter(self):
        """主账号没有 tenant_id → 不添加任何过滤"""
        user = create_test_user(id=1, account_type=AccountType.OWNER, tenant_id=None)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        assert _has_where_clause(result) is False


# ============================================================
# 5. scope_label tests
# ============================================================

class TestScopeLabel:
    """scope_label 标签生成"""

    def test_sub_returns_sub(self):
        """子账号返回 "sub" """
        user = create_test_user(account_type=AccountType.SUB)
        assert scope_label(user) == "sub"

    def test_owner_returns_owner(self):
        """主账号返回 "owner" """
        user = create_test_user(account_type=AccountType.OWNER)
        assert scope_label(user) == "owner"

    def test_none_returns_owner(self):
        """None 返回 "owner"（缺省行为）"""
        assert scope_label(None) == "owner"


# ============================================================
# 6. apply_to_statement alias test
# ============================================================

class TestApplyToStatement:
    """apply_to_statement 别名"""

    def test_apply_to_statement_matches_apply_to_query(self):
        """apply_to_statement 与 apply_to_query 行为一致"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self", tenant_id=42)
        query = select(MockLead.id)
        f = DataScopeFilter(user)
        r1 = f.apply_to_query(query, MockLead)
        r2 = f.apply_to_statement(query, MockLead)
        assert str(r1.compile(compile_kwargs={"literal_binds": False})) == str(r2.compile(compile_kwargs={"literal_binds": False}))


# ============================================================
# 7. Edge cases
# ============================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_model_has_no_tenant_column_skips_tenant_filter(self):
        """模型没有 tenant 列 → 跳过 tenant 过滤，只添加 owner_user_id"""
        class ModelWithoutTenant:
            __tablename__ = "notenant"
            id = Column(Integer, primary_key=True)
            owner_user_id = Column(Integer)
            created_by = Column(Integer)

        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self", tenant_id=42)
        query = select(ModelWithoutTenant.id)
        result = DataScopeFilter(user).apply_to_query(query, ModelWithoutTenant)
        # 1 param: owner_user_id only (no tenant_id column on model)
        assert _count_conditions(result) == 1

    def test_sub_self_scope_returns_correct_where_count(self):
        """全面的 param 计数验证"""
        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="self", tenant_id=42)
        query = select(MockLead.id)
        result = DataScopeFilter(user).apply_to_query(query, MockLead)
        # 2 params: tenant_id + owner_user_id
        assert _count_conditions(result) == 2

    def test_department_scope_no_dept_on_model_falls_back(self):
        """department 范围但模型没有 department_id → 回退到 owner"""
        class ModelWithoutDept:
            __tablename__ = "nodept"
            id = Column(Integer, primary_key=True)
            tenant_id = Column(Integer)
            owner_user_id = Column(Integer)

        user = create_test_user(id=123, account_type=AccountType.SUB, data_scope="department",
                              department_id=10, tenant_id=42)
        query = select(ModelWithoutDept.id)
        result = DataScopeFilter(user).apply_to_query(query, ModelWithoutDept)
        # 2 params: tenant_id + owner_user_id (fallback)
        assert _count_conditions(result) == 2