# Enhancement Point 1: Multi-Tenancy & Enterprise Isolation

## 问题陈述

**当前状态：** 架构中提到了企业版，但没有详细说明多租户架构

**核心问题：**
```
场景：大型企业有多个部门
├─ 销售部门用鎏灏
├─ 采购部门用鎏灏
├─ HR部门用鎏灏
└─ 但数据必须严格隔离

关键问题：
├─ 数据隔离怎么保证？
├─ 权限怎么分级管理？
├─ 成本怎么分摊？
├─ 审计怎么分离？
└─ 性能怎么保障？
```

---

## 完整解决方案

### 1. Multi-Tenancy Architecture（多租户架构）

#### 1.1 租户隔离模型

```yaml
租户层级结构:
Organization（组织）
  ├─ Tenant（租户）
  │   ├─ Department（部门）
  │   │   ├─ Team（团队）
  │   │   │   └─ User（用户）
  │   │   └─ Team
  │   └─ Department
  └─ Tenant

示例：
腾讯集团（Organization）
  ├─ 腾讯游戏（Tenant）
  │   ├─ 天美工作室（Department）
  │   │   ├─ 王者荣耀团队（Team）
  │   │   │   ├─ 张三（User）
  │   │   │   └─ 李四（User）
  │   │   └─ 和平精英团队（Team）
  │   └─ 光子工作室（Department）
  └─ 腾讯视频（Tenant）
```

#### 1.2 数据隔离策略

```yaml
数据隔离级别:

Level 1: Database-Level Isolation（数据库级隔离）
├─ 适用场景: 超大型企业（10,000+ users）
├─ 方案: 每个租户独立数据库
├─ 优点:
│   ├─ 完全隔离，安全性最高
│   ├─ 性能不相互影响
│   ├─ 可独立备份/恢复
│   └─ 满足严格合规要求
├─ 缺点:
│   ├─ 成本最高
│   ├─ 运维复杂
│   └─ 跨租户分析困难
└─ 实现:
    PostgreSQL: 每个租户一个独立数据库
    MongoDB: 每个租户一个独立集群

Level 2: Schema-Level Isolation（模式级隔离）
├─ 适用场景: 大型企业（1,000-10,000 users）
├─ 方案: 同一数据库，不同Schema
├─ 优点:
│   ├─ 平衡隔离性和成本
│   ├─ 运维相对简单
│   └─ 跨租户分析可行
├─ 缺点:
│   ├─ 部分隔离（共享连接池）
│   └─ 性能可能相互影响
└─ 实现:
    PostgreSQL: CREATE SCHEMA tenant_123
    设置 search_path = tenant_123

Level 3: Row-Level Isolation（行级隔离）
├─ 适用场景: 中小企业（100-1,000 users）
├─ 方案: 同一表，tenant_id字段区分
├─ 优点:
│   ├─ 成本最低
│   ├─ 开发简单
│   ├─ 跨租户查询方便
│   └─ 资源利用率高
├─ 缺点:
│   ├─ 安全风险最高（代码bug可能泄露）
│   ├─ 性能相互影响
│   └─ 数据量大时查询慢
└─ 实现:
    每个表添加 tenant_id 列
    所有查询强制 WHERE tenant_id = ?
    数据库Row-Level Security (RLS)
```

#### 1.3 推荐方案（混合模式）

```python
# liuhao/core/multi_tenancy/tenant_manager.py

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

class IsolationLevel(Enum):
    """隔离级别"""
    DATABASE = "database"  # 数据库级
    SCHEMA = "schema"      # 模式级
    ROW = "row"           # 行级

class TenantTier(Enum):
    """租户等级"""
    ENTERPRISE = "enterprise"     # 企业版（数据库级）
    BUSINESS = "business"         # 商业版（模式级）
    PROFESSIONAL = "professional" # 专业版（行级）
    STARTER = "starter"          # 入门版（行级）

@dataclass
class TenantConfig:
    """租户配置"""
    tenant_id: str
    organization_id: str
    tier: TenantTier
    isolation_level: IsolationLevel
    max_users: int
    max_storage_gb: int
    max_ai_tokens_per_month: int
    custom_domain: Optional[str] = None
    dedicated_resources: bool = False
    
class TenantManager:
    """多租户管理器"""
    
    def __init__(self):
        self.tenant_configs: Dict[str, TenantConfig] = {}
        
    def determine_isolation_level(self, tier: TenantTier) -> IsolationLevel:
        """根据租户等级确定隔离级别"""
        mapping = {
            TenantTier.ENTERPRISE: IsolationLevel.DATABASE,
            TenantTier.BUSINESS: IsolationLevel.SCHEMA,
            TenantTier.PROFESSIONAL: IsolationLevel.ROW,
            TenantTier.STARTER: IsolationLevel.ROW,
        }
        return mapping[tier]
    
    def get_database_connection(self, tenant_id: str):
        """获取租户数据库连接"""
        config = self.tenant_configs[tenant_id]
        
        if config.isolation_level == IsolationLevel.DATABASE:
            # 独立数据库
            return self._get_dedicated_db_connection(tenant_id)
        elif config.isolation_level == IsolationLevel.SCHEMA:
            # 独立Schema
            conn = self._get_shared_db_connection()
            conn.execute(f"SET search_path TO tenant_{tenant_id}")
            return conn
        else:
            # 行级隔离
            return self._get_shared_db_connection()
    
    def ensure_data_isolation(self, tenant_id: str, query: str) -> str:
        """确保数据隔离（行级隔离时自动添加tenant_id过滤）"""
        config = self.tenant_configs[tenant_id]
        
        if config.isolation_level == IsolationLevel.ROW:
            # 自动注入tenant_id过滤条件
            if "WHERE" in query.upper():
                query = query.replace("WHERE", f"WHERE tenant_id = '{tenant_id}' AND")
            else:
                query += f" WHERE tenant_id = '{tenant_id}'"
        
        return query
    
    def create_tenant(self, config: TenantConfig):
        """创建租户"""
        if config.isolation_level == IsolationLevel.DATABASE:
            self._create_dedicated_database(config.tenant_id)
        elif config.isolation_level == IsolationLevel.SCHEMA:
            self._create_schema(config.tenant_id)
        else:
            # 行级隔离不需要额外创建
            pass
        
        self.tenant_configs[config.tenant_id] = config
        
    def _create_dedicated_database(self, tenant_id: str):
        """创建独立数据库"""
        db_name = f"liuhao_tenant_{tenant_id}"
        # 创建数据库、表结构、索引等
        pass
    
    def _create_schema(self, tenant_id: str):
        """创建独立Schema"""
        schema_name = f"tenant_{tenant_id}"
        # CREATE SCHEMA, CREATE TABLES, etc.
        pass
```

---

### 2. 企业级权限管理（RBAC + ABAC）

#### 2.1 角色定义

```yaml
系统预定义角色:

Organization Level（组织级）:
├─ Organization Admin
│   ├─ 管理所有租户
│   ├─ 分配租户资源
│   ├─ 查看所有审计日志
│   └─ 管理计费
│
└─ Organization Viewer
    └─ 只读访问所有租户数据

Tenant Level（租户级）:
├─ Tenant Admin
│   ├─ 管理本租户所有资源
│   ├─ 创建/删除部门和用户
│   ├─ 配置AI权限
│   └─ 查看本租户审计日志
│
├─ Tenant Manager
│   ├─ 管理部门和团队
│   ├─ 管理用户
│   └─ 配置基础设置
│
└─ Tenant Viewer
    └─ 只读访问本租户数据

Department Level（部门级）:
├─ Department Admin
│   ├─ 管理本部门资源
│   ├─ 管理团队和用户
│   └─ 配置部门AI权限
│
└─ Department Member
    └─ 使用部门分配的资源

Team Level（团队级）:
├─ Team Lead
│   ├─ 管理团队成员
│   ├─ 分配团队任务
│   └─ 查看团队数据
│
└─ Team Member
    └─ 使用团队资源
```

#### 2.2 权限矩阵

```yaml
权限维度:

数据权限:
├─ Own（自己的数据）
├─ Team（团队的数据）
├─ Department（部门的数据）
├─ Tenant（租户的数据）
└─ Organization（组织的数据）

操作权限:
├─ Create（创建）
├─ Read（读取）
├─ Update（更新）
├─ Delete（删除）
├─ Execute（执行AI任务）
├─ Export（导出）
└─ Admin（管理）

AI权限:
├─ AI Usage Limit（AI使用限额）
├─ Model Access（可访问的模型）
├─ Autonomous Level（自主权限级别）
├─ Approval Required（是否需要审批）
└─ Sensitive Operations（敏感操作权限）

示例权限配置:
Team Member:
  数据权限:
    - Read: Own, Team
    - Create: Own
    - Update: Own
    - Delete: Own
  AI权限:
    - Usage Limit: 10,000 tokens/day
    - Models: GPT-4, Claude
    - Autonomous: Low（需要审批大部分操作）
    - Sensitive Ops: Denied

Department Admin:
  数据权限:
    - Read: Department
    - Create: Department
    - Update: Department
    - Delete: Own, Team
    - Export: Department
  AI权限:
    - Usage Limit: 100,000 tokens/day
    - Models: All
    - Autonomous: Medium（小事自动，大事审批）
    - Sensitive Ops: Restricted
```

#### 2.3 实现代码

```python
# liuhao/core/rbac/permission_manager.py

from typing import List, Set
from enum import Enum

class Permission(Enum):
    """权限枚举"""
    READ_OWN = "read:own"
    READ_TEAM = "read:team"
    READ_DEPARTMENT = "read:department"
    READ_TENANT = "read:tenant"
    CREATE_OWN = "create:own"
    UPDATE_OWN = "update:own"
    DELETE_OWN = "delete:own"
    EXECUTE_AI = "execute:ai"
    EXPORT_DATA = "export:data"
    MANAGE_USERS = "manage:users"
    # ... more permissions

class Role(Enum):
    """角色枚举"""
    ORG_ADMIN = "org_admin"
    TENANT_ADMIN = "tenant_admin"
    DEPT_ADMIN = "dept_admin"
    TEAM_LEAD = "team_lead"
    TEAM_MEMBER = "team_member"

class PermissionManager:
    """权限管理器"""
    
    # 角色-权限映射
    ROLE_PERMISSIONS = {
        Role.ORG_ADMIN: {
            Permission.READ_TENANT,
            Permission.MANAGE_USERS,
            # ... all permissions
        },
        Role.TENANT_ADMIN: {
            Permission.READ_TENANT,
            Permission.CREATE_OWN,
            Permission.MANAGE_USERS,
            # ...
        },
        Role.TEAM_MEMBER: {
            Permission.READ_OWN,
            Permission.READ_TEAM,
            Permission.CREATE_OWN,
            Permission.UPDATE_OWN,
            Permission.EXECUTE_AI,
        }
    }
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_id: str
    ) -> bool:
        """检查用户是否有权限"""
        user = self._get_user(user_id)
        resource = self._get_resource(resource_id)
        
        # 1. 检查角色权限
        if not self._has_role_permission(user.roles, permission):
            return False
        
        # 2. 检查数据范围权限
        if not self._check_data_scope(user, resource, permission):
            return False
        
        # 3. 检查属性权限（ABAC）
        if not self._check_attributes(user, resource, permission):
            return False
        
        return True
    
    def _check_data_scope(self, user, resource, permission):
        """检查数据范围权限"""
        if permission == Permission.READ_OWN:
            return resource.owner_id == user.id
        elif permission == Permission.READ_TEAM:
            return resource.team_id == user.team_id
        elif permission == Permission.READ_DEPARTMENT:
            return resource.department_id == user.department_id
        elif permission == Permission.READ_TENANT:
            return resource.tenant_id == user.tenant_id
        return False
```

---

### 3. 成本分摊机制

#### 3.1 计费模型

```yaml
分层计费:

Tenant Level（租户级）:
├─ 基础订阅费用
│   ├─ Enterprise: $10,000/月
│   ├─ Business: $999/月
│   └─ Professional: $299/月
│
├─ 资源用量费用
│   ├─ AI Token使用
│   ├─ 存储空间
│   ├─ API调用次数
│   └─ 带宽使用
│
└─ 增值服务
    ├─ 专属客户经理
    ├─ 定制开发
    └─ 培训服务

Department Level（部门级）:
├─ 资源分配
│   ├─ AI Token配额: 按比例分配
│   ├─ 存储配额: 按比例分配
│   └─ 用户数配额
│
└─ 成本追踪
    ├─ 实际使用量
    ├─ 成本归属
    └─ 超额告警

User Level（用户级）:
├─ 个人用量统计
├─ 成本归因
└─ 使用报告
```

#### 3.2 成本分摊实现

```python
# liuhao/core/billing/cost_allocation.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class UsageRecord:
    """用量记录"""
    tenant_id: str
    department_id: str
    user_id: str
    resource_type: str  # ai_tokens, storage, api_calls
    amount: float
    timestamp: datetime
    cost_usd: float

class CostAllocationManager:
    """成本分摊管理器"""
    
    def record_usage(self, record: UsageRecord):
        """记录资源使用"""
        # 1. 记录到时序数据库（ClickHouse/TimescaleDB）
        self._save_to_timeseries_db(record)
        
        # 2. 更新实时配额
        self._update_quota(record)
        
        # 3. 检查是否超额
        if self._is_over_quota(record):
            self._send_alert(record)
    
    def calculate_department_cost(
        self,
        tenant_id: str,
        department_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """计算部门成本"""
        query = f"""
        SELECT 
            resource_type,
            SUM(cost_usd) as total_cost
        FROM usage_records
        WHERE tenant_id = '{tenant_id}'
          AND department_id = '{department_id}'
          AND timestamp BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY resource_type
        """
        
        results = self._query_timeseries_db(query)
        
        return {
            "ai_tokens": results.get("ai_tokens", 0),
            "storage": results.get("storage", 0),
            "api_calls": results.get("api_calls", 0),
            "total": sum(results.values())
        }
    
    def generate_cost_report(self, tenant_id: str, month: str):
        """生成成本报告"""
        # 1. 租户总成本
        tenant_cost = self._calculate_tenant_cost(tenant_id, month)
        
        # 2. 各部门成本明细
        departments = self._get_departments(tenant_id)
        dept_costs = {}
        for dept in departments:
            dept_costs[dept.id] = self.calculate_department_cost(
                tenant_id, dept.id, month
            )
        
        # 3. Top用户排名
        top_users = self._get_top_users_by_cost(tenant_id, month, limit=10)
        
        return {
            "tenant_total": tenant_cost,
            "departments": dept_costs,
            "top_users": top_users,
            "breakdown": {
                "ai_tokens": ...,
                "storage": ...,
                "api_calls": ...,
            }
        }
```

---

### 4. 审计与合规

#### 4.1 审计日志系统

```yaml
审计日志范围:

数据访问审计:
├─ 谁（User）
├─ 何时（Timestamp）
├─ 访问了什么（Resource）
├─ 做了什么操作（Action）
├─ 从哪里访问（IP/Device）
├─ 结果如何（Success/Failure）
└─ 数据变更前后对比（Diff）

AI操作审计:
├─ AI任务ID
├─ 输入Prompt
├─ 输出Response
├─ 使用的模型
├─ Token消耗
├─ 执行时间
└─ 是否人工审批

权限变更审计:
├─ 谁修改了权限
├─ 修改了谁的权限
├─ 从什么权限改成什么
├─ 变更原因
└─ 审批流程

敏感操作审计:
├─ 数据导出
├─ 数据删除
├─ 权限提升
├─ 配置变更
└─ 系统管理

合规要求:
├─ 日志不可篡改（Write-once）
├─ 日志保留期限（7年+）
├─ 实时监控告警
├─ 定期审计报告
└─ 满足SOC2/ISO27001
```

#### 4.2 实现示例

```python
# liuhao/core/audit/audit_logger.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib

@dataclass
class AuditLog:
    """审计日志"""
    id: str
    tenant_id: str
    user_id: str
    action: str  # READ, CREATE, UPDATE, DELETE, EXECUTE
    resource_type: str
    resource_id: str
    timestamp: datetime
    ip_address: str
    user_agent: str
    success: bool
    error_message: Optional[str] = None
    data_before: Optional[Dict] = None
    data_after: Optional[Dict] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # 防篡改
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None

class AuditLogger:
    """审计日志器"""
    
    def __init__(self):
        self.previous_hash = None
    
    def log(self, log: AuditLog):
        """记录审计日志"""
        # 1. 计算哈希（防篡改）
        log.previous_hash = self.previous_hash
        log.current_hash = self._calculate_hash(log)
        self.previous_hash = log.current_hash
        
        # 2. 写入不可变存储（Append-only）
        self._write_to_immutable_storage(log)
        
        # 3. 实时告警（如果是敏感操作）
        if self._is_sensitive_operation(log):
            self._send_alert(log)
        
        # 4. 写入搜索引擎（用于查询）
        self._index_to_elasticsearch(log)
    
    def _calculate_hash(self, log: AuditLog) -> str:
        """计算哈希值"""
        data = f"{log.previous_hash}{log.tenant_id}{log.user_id}{log.action}{log.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def verify_integrity(self, log_id: str) -> bool:
        """验证日志完整性"""
        log = self._get_log(log_id)
        expected_hash = self._calculate_hash(log)
        return log.current_hash == expected_hash
    
    def search_logs(
        self,
        tenant_id: str,
        filters: Dict,
        start_time: datetime,
        end_time: datetime
    ):
        """搜索审计日志"""
        # 使用Elasticsearch进行复杂查询
        query = {
            "bool": {
                "must": [
                    {"term": {"tenant_id": tenant_id}},
                    {"range": {"timestamp": {"gte": start_time, "lte": end_time}}}
                ],
                "filter": []
            }
        }
        
        for key, value in filters.items():
            query["bool"]["filter"].append({"term": {key: value}})
        
        return self._search_elasticsearch(query)
```

---

### 5. 性能隔离

#### 5.1 资源配额管理

```yaml
租户资源配额:

计算资源:
├─ CPU配额: 按租户限制
├─ 内存配额: 按租户限制
├─ 并发请求数: Rate Limiting
└─ AI Token配额: 每月/每天限额

存储资源:
├─ 数据库存储配额
├─ 对象存储配额
├─ 备份存储配额
└─ 日志存储配额

网络资源:
├─ 带宽限制
├─ API调用频率限制
├─ WebSocket连接数限制
└─ 并发上传/下载限制

AI资源:
├─ 模型访问权限
├─ Token使用配额
├─ 并发AI请求数
└─ 响应优先级
```

#### 5.2 租户优先级队列

```python
# liuhao/core/multi_tenancy/resource_manager.py

from enum import Enum
from typing import Dict
import asyncio

class TenantPriority(Enum):
    """租户优先级"""
    CRITICAL = 1      # Enterprise客户
    HIGH = 2          # Business客户
    NORMAL = 3        # Professional客户
    LOW = 4           # Starter客户

class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        # 为不同优先级创建不同的队列
        self.queues = {
            TenantPriority.CRITICAL: asyncio.Queue(),
            TenantPriority.HIGH: asyncio.Queue(),
            TenantPriority.NORMAL: asyncio.Queue(),
            TenantPriority.LOW: asyncio.Queue(),
        }
        self.quotas: Dict[str, ResourceQuota] = {}
    
    async def submit_task(self, tenant_id: str, task):
        """提交任务"""
        # 1. 检查配额
        if not self._check_quota(tenant_id):
            raise QuotaExceededError(f"Tenant {tenant_id} quota exceeded")
        
        # 2. 获取租户优先级
        priority = self._get_tenant_priority(tenant_id)
        
        # 3. 加入对应优先级队列
        await self.queues[priority].put((tenant_id, task))
        
        # 4. 更新配额使用
        self._update_quota_usage(tenant_id, task)
    
    async def process_tasks(self):
        """处理任务（优先级调度）"""
        while True:
            # 按优先级顺序处理
            for priority in [
                TenantPriority.CRITICAL,
                TenantPriority.HIGH,
                TenantPriority.NORMAL,
                TenantPriority.LOW
            ]:
                if not self.queues[priority].empty():
                    tenant_id, task = await self.queues[priority].get()
                    await self._execute_task(tenant_id, task)
                    break
            else:
                # 所有队列都空，等待一会
                await asyncio.sleep(0.1)
    
    def _check_quota(self, tenant_id: str) -> bool:
        """检查配额"""
        quota = self.quotas.get(tenant_id)
        if not quota:
            return False
        
        # 检查各项配额
        if quota.ai_tokens_used >= quota.ai_tokens_limit:
            return False
        if quota.api_calls_today >= quota.api_calls_limit:
            return False
        if quota.concurrent_requests >= quota.max_concurrent:
            return False
        
        return True
```

---

## 总结

**多租户架构的核心要点：**

1. **数据隔离**：根据租户等级选择合适的隔离级别
2. **权限管理**：RBAC + ABAC 结合，细粒度控制
3. **成本分摊**：透明的成本追踪和分摊机制
4. **审计合规**：完整的审计日志，满足合规要求
5. **性能隔离**：资源配额和优先级队列，保证公平性

**实施优先级：**
- P0: 数据隔离、基础权限管理
- P1: 成本分摊、审计日志
- P2: 高级权限、性能隔离
- P3: 优化和完善

---

## 下一步

完善点2：[性能与规模化保障](./02_PERFORMANCE_SCALABILITY.md)
