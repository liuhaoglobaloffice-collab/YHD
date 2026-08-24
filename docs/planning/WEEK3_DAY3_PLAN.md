# 📋 Week 3 Day 3 执行计划

**日期**: 2026-08-24  
**目标**: Business API 完善与测试加固  
**负责人**: LiuHao AI-OS 开发团队

---

## 🎯 核心目标

### 主要目标
1. ✅ 创建 Business API 集成测试套件
2. ✅ 补充 Business Task API 异常场景测试
3. ✅ 提升 Business 模块测试覆盖率至 70%+
4. ✅ 修复 E2E workflow 测试失败问题
5. ✅ 完成 Week 3 Day 3 测试报告

### 质量指标
- Business API 集成测试通过率: **100%**
- Business 模块覆盖率: **70%+** (当前: 19%)
- E2E 测试通过率: **>=75%** (当前: 2/6)
- 整体测试通过率: **>=95%** (当前: 93.5%)

---

## 📊 当前状态分析

### ✅ 已完成
- Business 单元测试: **35/35 通过** (100%)
- Business Service 逻辑: 已实现并测试
- Business Registry: 已实现并测试
- Business Models: 已实现并测试

### ⚠️ 待完成
- Business API 集成测试: **0 个测试**
- Business API 异常场景: 未覆盖
- E2E Workflow 测试: **2/6 通过** (33%)
- Supplier E2E 测试: **1/6 通过** (17%)

---

## 🔧 执行任务

### 任务 1: 创建 Business API 集成测试 (优先级 P0)

**文件**: `tests/integration/test_business_api.py`

**测试场景**:

#### 1.1 Business Task CRUD (8 个测试)
- ✅ test_create_business_task_success
- ✅ test_create_business_task_without_permission
- ✅ test_create_business_task_invalid_domain
- ✅ test_get_business_task_success
- ✅ test_get_business_task_not_found
- ✅ test_list_business_tasks_with_filters
- ✅ test_update_business_task_status (如果API存在)
- ✅ test_delete_business_task (如果API存在)

#### 1.2 Business Metrics (2 个测试)
- ✅ test_get_domain_metrics_success
- ✅ test_get_domain_metrics_without_permission

#### 1.3 异常场景 (5 个测试)
- ✅ test_create_task_missing_required_fields
- ✅ test_create_task_invalid_priority
- ✅ test_create_task_invalid_json_context
- ✅ test_list_tasks_invalid_filter_values
- ✅ test_unauthorized_access_business_api

**预期结果**: **15/15 测试通过**

---

### 任务 2: 补充 Business Service 异常测试 (优先级 P1)

**文件**: `tests/test_business/test_service.py`

**新增测试场景** (5 个):
- ✅ test_create_task_with_invalid_user_id
- ✅ test_assign_task_to_nonexistent_employee
- ✅ test_update_nonexistent_task
- ✅ test_complete_task_without_starting
- ✅ test_list_tasks_with_invalid_pagination

**预期结果**: **40/40 测试通过** (当前 35 + 新增 5)

---

### 任务 3: 修复 E2E Workflow 测试 (优先级 P1)

**文件**: `tests/integration/test_supplier_e2e.py`

**失败测试**:
1. ❌ test_complete_supplier_onboarding_workflow
2. ❌ test_supplier_data_migration_workflow
3. ❌ test_supplier_offboarding_workflow
4. ❌ test_supplier_status_transitions
5. ❌ test_supplier_risk_score_impact

**修复策略**:
1. 分析失败原因（读取测试输出）
2. 修复测试数据问题
3. 修复测试断言问题
4. 确保 E2E 流程完整性

**预期结果**: **5/6 测试通过** (>=83%)

---

### 任务 4: 提升 Business 模块覆盖率 (优先级 P2)

**目标模块覆盖率**:

| 模块 | 当前 | 目标 | 策略 |
|------|------|------|------|
| `src/business/service.py` | 19% | 70%+ | 补充异常场景 + 边界测试 |
| `src/business/registry.py` | 27% | 75%+ | 补充错误处理测试 |
| `src/api/routes/business.py` | 64% | 80%+ | API 集成测试 |

**执行步骤**:
1. 运行覆盖率分析: `pytest --cov=src/business --cov-report=html`
2. 识别未覆盖代码路径
3. 补充针对性测试
4. 验证覆盖率提升

---

## 📈 成功标准

### 必须达成 (P0)
- ✅ Business API 集成测试: **15/15 通过** (100%)
- ✅ Business 模块覆盖率: **>=70%**
- ✅ 整体测试通过率: **>=95%**

### 应该达成 (P1)
- ✅ Business Service 异常测试: **40/40 通过**
- ✅ E2E Workflow 测试: **>=5/6 通过** (83%)
- ✅ 代码质量: 无新增 linting 错误

### 可以达成 (P2)
- ✅ Performance 测试修复: 减少失败数量
- ✅ Migration 测试修复 (BUG-011)
- ✅ 文档更新: Week 3 Day 3 完成报告

---

## 🚀 执行顺序

### Phase 1: Business API 集成测试 (2-3小时)
1. 创建测试文件 `tests/integration/test_business_api.py`
2. 实现 15 个集成测试场景
3. 运行测试并修复失败
4. 验证 100% 通过

### Phase 2: Business Service 异常测试 (1-2小时)
1. 补充 5 个异常场景测试
2. 运行 `pytest tests/test_business/test_service.py`
3. 验证 40/40 通过

### Phase 3: E2E Workflow 测试修复 (1-2小时)
1. 读取 E2E 测试失败详情
2. 修复测试数据/断言问题
3. 验证 5/6 通过

### Phase 4: 覆盖率提升与报告 (1小时)
1. 运行覆盖率分析
2. 验证目标达成
3. 生成 Week 3 Day 3 完成报告

**预计总耗时**: 5-8 小时

---

## 📝 交付物

### 必须交付
1. ✅ `tests/integration/test_business_api.py` - Business API 集成测试
2. ✅ `tests/test_business/test_service.py` - 更新后的 Service 测试
3. ✅ `tests/integration/test_supplier_e2e.py` - 修复后的 E2E 测试
4. ✅ `docs/reports/WEEK3_DAY3_COMPLETION_REPORT.md` - 完成报告

### 可选交付
- ✅ 覆盖率 HTML 报告 (`htmlcov/`)
- ✅ 测试质量分析报告
- ✅ Git commit 记录

---

## ⚠️ 风险与依赖

### 技术风险
- **中**: E2E 测试可能涉及复杂的数据依赖
- **低**: Business API 测试相对独立，风险可控
- **低**: 覆盖率提升可能需要重构部分代码

### 依赖项
- ✅ Supplier API 修复完成 (Day 2 已完成)
- ✅ Database schema 稳定
- ✅ RBAC 权限系统正常工作

### 缓解措施
- E2E 测试失败：先修复简单场景，复杂场景标记为 P2
- 覆盖率不足：优先覆盖核心业务逻辑路径
- 时间不足：P2 任务延后至 Day 4

---

## 🎯 下一步 (Week 3 Day 4)

根据 Day 3 完成情况，Day 4 计划：

### 如果 Day 3 目标全部达成
- 开始 Migration 测试修复 (BUG-011)
- 补充 API 性能测试
- 开始 Week 3 总结准备

### 如果 Day 3 部分达成
- 完成 Day 3 剩余 P1 任务
- P2 任务延后
- 调整 Week 3 总体计划

---

**计划制定时间**: 2026-08-24 03:45 PST  
**计划审核**: LiuHao AI-OS 开发团队  
**计划状态**: ✅ 已批准，开始执行
