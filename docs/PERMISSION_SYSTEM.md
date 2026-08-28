# 权限系统文档

## 概述

鎏灏 AI OS 的权限系统采用 **RBAC + ABAC 混合模型**，支持主/子账号分离、业务角色分工、数据范围控制和细粒度权限覆盖。

核心原则：
- **主账号 = 老板 / 总指挥**，拥有租户内全部权限和数据
- **子账号 = 被授权的 AI OS 操作人员**，只能在授权范围内操作
- **数据隔离**：租户间完全隔离，租户内通过 data_scope 控制可见范围

---

## 一、核心概念

### 1. 账号体系 (`AccountType`)

| 类型 | 枚举值 | 说明 |
|------|--------|------|
| 主账号 | `OWNER` | 老板级账号，拥有租户内全部权限和数据访问权 |
| 子账号 | `SUB` | 受限账号，由主账号创建或审批，权限受业务角色和数据范围控制 |

### 2. 业务角色 (`BusinessRole`)

业务角色定义子账号的岗位职责，每个角色对应一组预设权限。

| 角色 | 枚举值 | 适用岗位 | 典型权限 |
|------|--------|----------|----------|
| 销售 | `SALES` | 客户开发、CRM跟进 | 线索管理、平台消息、报价单、工作流 |
| 采购 | `PURCHASING` | 供应商搜索、采购谈判 | 供应商管理、报关数据、任务 |
| 运营 | `OPERATIONS` | 数据运营、SEO、内容发布 | 独立站、SEO、审计、仪表盘 |
| AI管理员 | `AI_ADMIN` | 管理AI员工/技能/模型 | Agent、Workforce、知识库、AI指令 |
| 通用 | `GENERAL` | 多功能综合岗 | 跨模块基础读写权限 |

### 3. 系统角色 (`RoleEnum`)

系统角色作为兜底层级，仅在子账号 **未分配业务角色** 时生效。

| 角色 | 枚举值 | 说明 |
|------|--------|------|
| 管理员 | `ADMIN` | 系统管理权限 |
| 用户 | `USER` | 基础操作权限 |
| 只读 | `VIEWER` | 仅读权限 |

### 4. 数据范围 (`data_scope`)

控制子账号能看到的业务数据范围。

| 范围 | 枚举值 | 说明 |
|------|--------|------|
| 仅本人 | `self` | 只能看到自己创建的数据（默认） |
| 本部门 | `department` | 只能看到本部门的数据 |
| 全公司 | `all` | 能看到租户内所有数据（不限用户） |

### 5. 审批状态 (`ApprovalStatus`)

子账号注册后的生命周期状态。

| 状态 | 说明 |
|------|------|
| `pending` | 待主账号审核 |
| `approved` | 已通过，账号激活 |
| `rejected` | 已拒绝，无法登录 |

---

## 二、权限检查优先级

`has_permission()` 函数的检查顺序（从高到低）：

```
① 账号停用           → 直接拒绝
② 主账号(OWNER)       → 直接放行
③ permissions_config  → 自定义配置覆盖（最高优先级）
④ business_role       → 业务角色预设（次优先级）
⑤ system_role         → 系统角色兜底（仅当无业务角色时）
```

**关键行为**：如果一个子账号有业务角色，但某权限不在该角色的预设列表中，则直接拒绝，**不回退**到系统角色权限。这是为了防止业务角色获得不应有的权限。

---

## 三、数据范围过滤

### 使用方式

```python
from src.identity.visibility import DataScopeFilter

# 1. 应用到 SQL 查询（推荐）
filter_ = DataScopeFilter(current_user)
query = select(Supplier).select_from(Supplier)
query = filter_.apply_to_query(query, Supplier, owner_field="created_by")

# 2. 单条记录可见性检查
filter_.can_access_record(record_user_id=owner_id)

# 3. 获取可见用户 ID 集合（兼容旧接口）
user_ids = filter_.visible_user_ids()
```

### 过滤逻辑

```
主账号(OWNER):
  → 始终添加 tenant_id 过滤
  → 不过滤用户级

子账号(self):
  → tenant_id 过滤
  + owner_user_id = 自己

子账号(department):
  → tenant_id 过滤
  + department_id = 自己部门
  → 若没有 department_id 字段，回退到 self

子账号(all):
  → tenant_id 过滤
  → 不过滤用户级
```

---

## 四、权限配置（`permissions_config`）

主账号可为每个子账号单独调整权限，以 JSON 格式存储。

```json
{
  "lead:create": true,
  "lead:delete": false,
  "supplier:create": true,
  "system:admin": false
}
```

- `true`：额外授予该权限（即使业务角色预设中不包含）
- `false`：禁用该权限（即使业务角色预设中包含）

**注意**：主账号的 `permissions_config` 无效，主账号始终拥有全部权限。

---

## 五、User 模型关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `account_type` | `AccountType` | 主账号/子账号 |
| `business_role` | `BusinessRole` | 业务角色（子账号的岗位） |
| `data_scope` | `str` | 数据范围（self/department/all） |
| `permissions_config` | `dict` | 自定义权限配置（JSON） |
| `parent_user_id` | `int` | 子账号关联的主账号 ID |
| `approval_status` | `str` | 审批状态（pending/approved/rejected） |
| `tenant_id` | `str` | 租户 ID |
| `is_active` | `bool` | 账号是否启用 |
| `ai_budget_monthly` | `float` | 子账号月度 AI 预算（USD） |

---

## 六、API 路由集成示例

```python
from src.identity.visibility import DataScopeFilter
from src.identity.rbac import require_permission, Permission

@router.get("/suppliers")
async def list_suppliers(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission(Permission.SUPPLIER_READ)),
):
    # 1. 权限检查（由 Depends 自动完成）
    # 2. 数据范围过滤
    filter_ = DataScopeFilter(current_user)
    query = select(Supplier)
    query = filter_.apply_to_query(query, Supplier, owner_field="created_by")
    result = await session.execute(query)
    return result.scalars().all()
```

---

## 七、测试覆盖

所有测试文件位于 `tests/` 目录下：

| 文件 | 类型 | 用例数 | 覆盖内容 |
|------|------|--------|----------|
| `tests/identity/test_visibility_data_scope.py` | 单元测试 | 35 | DataScopeFilter 核心逻辑 |
| `tests/identity/test_business_roles_permissions.py` | 单元测试 | 21 | 业务角色权限检查优先级 |
| `tests/integration/test_account_system.py` | 集成测试 | 21 | 登录/注册/审批/授权 |
| `tests/integration/test_data_scope_permissions.py` | 集成测试 | 34 | 真实子账号访问场景 |

运行测试：

```bash
# 运行所有权限相关测试
pytest tests/identity/ tests/integration/test_account_system.py tests/integration/test_data_scope_permissions.py -v

# 仅运行数据范围集成测试
pytest tests/integration/test_data_scope_permissions.py -v
```

---

## 八、常见场景

### 场景 1：创建子账号

```python
# 主账号创建子账号（不需要审批）
sub = User(
    username="sales_01",
    email="sales@company.com",
    account_type=AccountType.SUB,
    parent_user_id=owner.id,
    tenant_id=owner.tenant_id,
    business_role=BusinessRole.SALES,     # 销售角色
    data_scope="self",                    # 仅本人数据
    is_active=True,                       # 直接激活
    approval_status=ApprovalStatus.APPROVED.value,
    ai_budget_monthly=50.0,               # 月度预算 $50
)
```

### 场景 2：子账号自助注册 + 审核

```python
# 子账号注册（pending 状态）
sub = User(
    username="new_staff",
    email="staff@company.com",
    account_type=AccountType.SUB,
    parent_user_id=owner.id,
    tenant_id=owner.tenant_id,
    is_active=False,
    approval_status=ApprovalStatus.PENDING.value,
)

# 主账号审核通过
sub.approval_status = ApprovalStatus.APPROVED.value
sub.is_active = True
sub.business_role = BusinessRole.SALES  # 分配业务角色
sub.data_scope = "self"
```

### 场景 3：主账号调整权限

```python
# 临时禁用子账号的删除权限，同时额外授予供应商管理权限
sub.permissions_config = {
    "lead:delete": False,          # 覆盖：销售角色默认有删除权限，但禁用
    "supplier:create": True,       # 覆盖：销售角色默认无供应商创建，但授予
    "supplier:read": True,
}
```

### 场景 4：数据范围控制

```python
# 销售经理：可以看到所有销售数据
sub.data_scope = "all"

# 普通销售：只能看到自己跟进的数据
sub.data_scope = "self"

# 部门主管：只能看到本部门数据
sub.department_id = 10
sub.data_scope = "department"
```

---

## 九、关键文件索引

| 文件 | 作用 |
|------|------|
| [src/identity/models.py](file:///d:/LiuHao-AI-OS/src/identity/models.py) | User 模型定义，含 account_type、business_role、data_scope 等字段 |
| [src/identity/rbac.py](file:///d:/LiuHao-AI-OS/src/identity/rbac.py) | 权限枚举、业务角色预设、has_permission 检查逻辑 |
| [src/identity/visibility.py](file:///d:/LiuHao-AI-OS/src/identity/visibility.py) | DataScopeFilter 数据范围过滤器 |
| [src/identity/auth.py](file:///d:/LiuHao-AI-OS/src/identity/auth.py) | 认证工具（密码哈希、Token 生成/验证） |
| [tests/identity/test_visibility_data_scope.py](file:///d:/LiuHao-AI-OS/tests/identity/test_visibility_data_scope.py) | 数据范围过滤单元测试 |
| [tests/identity/test_business_roles_permissions.py](file:///d:/LiuHao-AI-OS/tests/identity/test_business_roles_permissions.py) | 业务角色权限单元测试 |
| [tests/integration/test_account_system.py](file:///d:/LiuHao-AI-OS/tests/integration/test_account_system.py) | 账号系统集成测试 |
| [tests/integration/test_data_scope_permissions.py](file:///d:/LiuHao-AI-OS/tests/integration/test_data_scope_permissions.py) | 数据范围 + 权限集成测试 |