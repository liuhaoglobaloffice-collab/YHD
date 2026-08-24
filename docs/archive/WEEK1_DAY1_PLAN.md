# 🚀 Week 1 Day 1 修复计划

**日期**: 2026-08-22  
**目标**: 从107个失败降到50个以下  
**策略**: 批量修复相同类型的错误

---

## 📊 测试现状

```yaml
总测试数: 482
通过: 372 (77.2%)
失败: 107 (22.2%)
跳过: 3 (0.6%)

当前测试通过率: 77.2%
目标测试通过率: 90%+
```

---

## 🔍 错误分类分析

### **Category 1: API变更导致的签名不匹配（50个错误，最优先）**

#### 1.1 CommandPriority.MEDIUM → CommandPriority.NORMAL
**影响**: 15个测试失败
**文件**:
- tests/test_ai_brain/test_command_processor.py (3个)
- tests/test_ai_brain/test_planner.py (12个)

**错误信息**:
```
AttributeError: type object 'CommandPriority' has no attribute 'MEDIUM'
```

**修复方案**:
```python
# 检查 src/ai_brain/models.py 或 src/models/task.py
# 如果 CommandPriority 是:
class CommandPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"  # 而不是 MEDIUM
    HIGH = "high"
    CRITICAL = "critical"

# 则批量替换测试文件中的 MEDIUM → NORMAL
```

**执行**: 
1. 检查 CommandPriority 定义
2. 批量替换 `CommandPriority.MEDIUM` → `CommandPriority.NORMAL`

---

#### 1.2 ParsedCommand 属性变更
**影响**: 7个测试失败
**文件**:
- tests/test_ai_brain/test_command_processor.py (2个)
- tests/test_ai_brain/test_planner.py (5个)

**错误信息**:
```
AttributeError: 'ParsedCommand' object has no attribute 'command_text'
TypeError: ParsedCommand.__init__() got an unexpected keyword argument 'command_text'
```

**修复方案**:
```python
# 检查 ParsedCommand 新定义
# 可能改名为 'text' 或 'content'
# 更新所有测试中的属性访问
```

---

#### 1.3 RBACService.check_permission() 签名变更
**影响**: 7个测试失败
**文件**: tests/test_api/test_service_integration.py

**错误信息**:
```
TypeError: RBACService.check_permission() missing 1 required positional argument: 'action'
```

**修复方案**:
```python
# 旧签名: check_permission(user, permission)
# 新签名: check_permission(user, resource, action)
# 更新所有调用点
```

---

#### 1.4 WorkflowService/WorkflowBridge API变更
**影响**: 8个测试失败

**错误**:
- `create_workflow()` 参数 `definition` → `description`
- `create_workflow_from_plan()` 参数变更
- `execute_workflow()` 缺少 `user` 参数
- 缺少 `get_workflow_status()` 方法

**修复**: 对齐新API签名

---

#### 1.5 AuditService.log_permission_denied() 签名变更
**影响**: 1个测试
**错误**: 缺少 `session` 和 `reason` 参数

---

### **Category 2: 数据模型变更（25个错误）**

#### 2.1 TaskType.AI_TASK 不存在
**影响**: 4个测试
**文件**: tests/test_api/test_service_integration.py

**错误信息**:
```
AttributeError: type object 'TaskType' has no attribute 'AI_TASK'
```

**修复**: 检查 TaskType 枚举，使用正确的类型名

---

#### 2.2 Position.SALES_REP 不存在
**影响**: 1个测试
**修复**: 检查 Position 枚举值

---

#### 2.3 Workflow 模型变更
**影响**: 7个测试
**错误**: `version` 参数不存在
**修复**: 移除测试中的 `version` 参数

---

#### 2.4 Task 模型 creator_id 约束
**影响**: 1个测试
**错误**: NOT NULL constraint failed: tasks.creator_id
**修复**: 创建测试任务时提供 `creator_id`

---

### **Category 3: 服务实现不完整（20个错误）**

#### 3.1 CompanyBrain 缺少 _entities 属性
**影响**: 6个测试
**原因**: 从内存实现迁移到数据库，但测试还在使用旧API

**修复**: 更新测试使用新的Repository模式

---

#### 3.2 MemoryService 缺少内存属性
**影响**: 9个测试
**原因**: 同样是迁移到数据库

**修复**: 使用Repository查询代替直接访问内存

---

#### 3.3 IntelligentPlanner 缺少 decompose() 方法
**影响**: 1个测试
**修复**: 检查方法名是否改为 `plan()` 或 `create_plan()`

---

### **Category 4: 测试逻辑问题（10个错误）**

#### 4.1 测试空命令但未抛出异常
**影响**: 1个测试
```python
# 测试期望抛出 ValueError，但实际没抛
```

---

#### 4.2 None.strip() 错误
**影响**: 1个测试
**修复**: 在 strip() 前检查 None

---

#### 4.3 导入错误
- `require_permission` 不在 `src.api.dependencies`
- `AuditLog` 不在 `src.database.models`

**修复**: 找到正确的导入路径

---

### **Category 5: 数据库迁移问题（4个错误）**

#### 5.1 迁移版本不匹配
**影响**: 3个测试
**错误**: 
- 期望版本 `83b280b69e5f` 但未找到
- 降级测试失败

**修复**: 
1. 检查 alembic/versions/ 目录
2. 确保最新迁移脚本存在
3. 可能需要重新生成迁移

---

### **Category 6: 业务逻辑问题（5个错误）**

#### 6.1 Identity Governance 自我操作限制
**影响**: 2个测试
**错误**: 
- Admin 无法禁用自己的账户
- 无法修改最后一个 admin 角色

**修复**: 测试中创建多个 admin 或修改测试逻辑

---

#### 6.2 会话管理测试缺少 db_session
**影响**: 5个测试
**修复**: 在测试中注入 db_session fixture

---

#### 6.3 KnowledgeRetrieval 测试断言不匹配
**影响**: 3个测试
**修复**: 调整断言匹配实际返回值

---

## ✅ Day 1 执行计划（6-8小时）

### **Phase 1: 快速批量修复（2小时）**

```bash
# Task 1: 修复 CommandPriority.MEDIUM → NORMAL (15个测试)
□ 1. 检查 CommandPriority 定义
□ 2. 批量替换测试文件
□ 3. 运行测试验证

# Task 2: 修复 ParsedCommand 属性 (7个测试)
□ 1. 检查 ParsedCommand 新属性名
□ 2. 更新测试代码
□ 3. 验证

# Task 3: 修复 TaskType/Position 枚举 (5个测试)
□ 1. 找到正确的枚举值
□ 2. 更新测试
□ 3. 验证

预计修复: 27个测试 ✅
预计通过率: 77% → 82%
```

---

### **Phase 2: API签名修复（2小时）**

```bash
# Task 4: RBACService.check_permission 签名 (7个测试)
□ 1. 确认新签名
□ 2. 更新所有调用
□ 3. 验证

# Task 5: WorkflowService API (8个测试)
□ 1. 对齐所有参数名
□ 2. 添加缺失的方法调用
□ 3. 验证

# Task 6: 其他API修复 (5个测试)
□ 修复 AuditService, AIEmployeeService 等

预计修复: 20个测试 ✅
预计通过率: 82% → 86%
```

---

### **Phase 3: 数据模型修复（1.5小时）**

```bash
# Task 7: Workflow 模型 (7个测试)
□ 移除 version 参数

# Task 8: Task 模型 (1个测试)
□ 添加 creator_id

预计修复: 8个测试 ✅
预计通过率: 86% → 88%
```

---

### **Phase 4: 服务实现修复（2小时）**

```bash
# Task 9: CompanyBrain 测试更新 (6个测试)
□ 使用 Repository 模式

# Task 10: MemoryService 测试更新 (9个测试)
□ 使用数据库查询替代内存访问

# Task 11: 会话管理测试 (5个测试)
□ 注入 db_session fixture

预计修复: 20个测试 ✅
预计通过率: 88% → 92%
```

---

### **Phase 5: 导入和测试逻辑（0.5小时）**

```bash
# Task 12: 修复导入错误 (2个测试)
□ 找到正确的导入路径

# Task 13: 测试逻辑修复 (3个测试)
□ 空命令测试
□ None 检查
□ 断言调整

预计修复: 5个测试 ✅
预计通过率: 92% → 93%
```

---

## 📊 Day 1 预期成果

```yaml
开始状态:
  - 通过: 372 (77.2%)
  - 失败: 107 (22.2%)

预期结束状态:
  - 通过: 450+ (93%+)
  - 失败: 30- (6%-)

修复进度:
  - Phase 1: 27个 ✅
  - Phase 2: 20个 ✅
  - Phase 3: 8个 ✅
  - Phase 4: 20个 ✅
  - Phase 5: 5个 ✅
  - 总计: 80个修复

剩余:
  - 数据库迁移问题: 4个（留到Day 2）
  - 复杂业务逻辑: 5个（留到Day 2）
  - KnowledgeRetrieval: 3个（留到Day 2）
```

---

## 🚀 立即开始

**第一个任务**: 检查 CommandPriority 定义

```bash
# 执行命令
rg "class CommandPriority" src/ -A 5
```

等待你的确认，我立即开始执行！💪
