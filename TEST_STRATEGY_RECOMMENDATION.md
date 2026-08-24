# 🎯 LiuHao AI OS 测试策略推荐

## 战略思路：风险驱动 + 快速见效

---

## 📅 四阶段实施计划

### 🔴 **第一阶段：安全基石（2-3 天）**
**目标：覆盖率 23% → 35%**

#### 优先级排序
1. `identity/auth.py` (39% → 95%)
   - ✅ JWT 令牌生成和验证
   - ✅ 密码哈希和验证
   - ✅ 会话管理
   - ✅ 登录/登出流程

2. `identity/rbac.py` (78% → 95%)
   - ✅ 角色权限检查
   - ✅ 资源访问控制
   - ✅ 权限继承
   - ✅ 动态权限评估

3. `multi_tenant/services.py` (0% → 80%)
   - ✅ 租户隔离验证
   - ✅ 数据泄漏防护
   - ✅ 跨租户访问阻断

4. `security/policy.py` (24% → 80%)
   - ✅ 安全策略执行
   - ✅ IP 白名单/黑名单
   - ✅ 速率限制

#### 关键测试用例
```python
# 必须包含的测试
- test_authentication_with_invalid_credentials()
- test_token_expiration_and_refresh()
- test_rbac_permission_denied()
- test_tenant_data_isolation()
- test_sql_injection_prevention()
- test_xss_prevention()
- test_rate_limiting()
```

#### 成功指标
- ✅ 安全相关模块覆盖率 > 90%
- ✅ 通过 OWASP Top 10 基础检查
- ✅ 零已知的身份认证漏洞

---

### 🟠 **第二阶段：执行引擎（1-2 天）**
**目标：覆盖率 35% → 45%**

#### 优先级排序
1. `tasks/executor.py` (0% → 85%)
   - ✅ 任务调度逻辑
   - ✅ 依赖图解析
   - ✅ 循环依赖检测
   - ✅ 并发执行控制
   - ✅ 失败重试机制

2. `workflow/executor.py` (0% → 85%)
   - ✅ 工作流步骤编排
   - ✅ 条件分支执行
   - ✅ 错误处理和回滚
   - ✅ 长流程稳定性

#### 关键测试用例
```python
# 必须包含的测试
- test_task_dependency_resolution()
- test_circular_dependency_detection()
- test_concurrent_task_execution()
- test_task_retry_with_exponential_backoff()
- test_workflow_step_rollback_on_failure()
- test_workflow_conditional_branching()
- test_long_running_workflow_stability()
```

#### 成功指标
- ✅ 执行引擎覆盖率 > 85%
- ✅ 100% 依赖解析测试通过
- ✅ 并发场景无竞态条件

---

### 🟡 **第三阶段：知识管理（2-3 天）**
**目标：覆盖率 45% → 60%**

#### 优先级排序
1. **先诊断现有测试失败原因**
   - 检查 `tests/test_knowledge/` 为何 0%
   - 修复环境依赖（向量数据库、Ollama）
   - 添加 mock 支持

2. `knowledge/retrieval.py` (0% → 80%)
   - ✅ 向量检索准确性
   - ✅ 混合搜索排序
   - ✅ 相似度阈值

3. `knowledge/company_brain.py` (0% → 70%)
   - ✅ 实体识别和提取
   - ✅ 事实关系推理
   - ✅ 知识图谱查询

4. `knowledge/memory.py` (0% → 75%)
   - ✅ 记忆存储和召回
   - ✅ 记忆优先级
   - ✅ 长期记忆衰减

#### 关键测试用例
```python
# 必须包含的测试
- test_vector_search_recall_rate()
- test_hybrid_search_ranking_quality()
- test_knowledge_graph_entity_extraction()
- test_memory_storage_and_retrieval()
- test_document_parsing_accuracy()
```

#### 成功指标
- ✅ 知识管理覆盖率 > 75%
- ✅ 检索召回率 > 90% (测试集)
- ✅ 知识图谱构建无错误

---

### 🟢 **第四阶段：端到端集成（2-3 天）**
**目标：覆盖率 60% → 75%+**

#### 优先级排序
1. **用户旅程测试**
   ```
   Journey 1: CEO 每日工作流
   - 登录 → 查看仪表板 → 审批请求 → 创建任务

   Journey 2: 员工执行任务
   - 登录 → 接收任务 → 调用 AI → 提交结果

   Journey 3: 供应商管理
   - 添加供应商 → 风险评估 → 审批流程
   ```

2. **API 层测试**
   - 所有 API 路由的正常流程
   - 错误处理和边界条件
   - 权限验证

3. **关键业务场景**
   - 营销任务创建和执行
   - 销售线索跟进
   - 运营自动化

#### 关键测试用例
```python
# 必须包含的测试
- test_ceo_dashboard_end_to_end()
- test_employee_task_execution_flow()
- test_supplier_risk_assessment_workflow()
- test_api_authentication_and_authorization()
- test_business_service_integration()
```

#### 成功指标
- ✅ 整体覆盖率 > 75%
- ✅ 所有关键用户旅程测试通过
- ✅ API 端到端测试覆盖主要流程

---

## 📊 预期成果

### 覆盖率提升路径
```
当前: 23%
阶段1: 35% (+12%)  [安全基石]
阶段2: 45% (+10%)  [执行引擎]
阶段3: 60% (+15%)  [知识管理]
阶段4: 75% (+15%)  [端到端]
```

### 风险降低
- 🔴 **高风险模块**：从 5 个减少到 0 个
- 🟡 **中风险模块**：从 4 个减少到 2 个
- 🟢 **低风险模块**：从 4 个增加到 11 个

### 质量保证
- ✅ 身份认证和授权：可信赖
- ✅ 数据隔离：企业级
- ✅ 执行稳定性：生产就绪
- ✅ AI 功能质量：有保障
- ✅ 用户体验：流畅无阻

---

## 🛠️ 实施建议

### 1. **并行开发策略**
如果团队有多人：
- Person A: 安全测试（阶段1）
- Person B: 执行引擎测试（阶段2）
- Person C: 知识管理测试修复（阶段3）

### 2. **持续集成**
每个阶段完成后：
```bash
# 运行测试并生成报告
pytest --cov=src --cov-report=html --cov-report=term-missing

# 验证覆盖率是否达标
coverage report --fail-under=X
```

### 3. **测试类型分布**
- **单元测试**: 60% (快速反馈)
- **集成测试**: 30% (模块协作)
- **端到端测试**: 10% (用户旅程)

### 4. **Mock 策略**
- 外部 AI 服务 (Ollama, OpenAI) → Mock
- 数据库 → 使用 SQLite 内存数据库
- Redis → 使用 fakeredis
- 文件系统 → 使用临时目录

### 5. **性能测试**
在功能测试完成后：
- API 压力测试 (已有框架)
- 数据库查询性能 (已有框架)
- AI 推理延迟测试

---

## 🎯 立即行动

### 选项 A：全面推进（推荐）
从阶段1开始，顺序执行全部四个阶段

### 选项 B：高风险优先
只做阶段1和阶段2，快速覆盖高风险区域

### 选项 C：核心功能
做阶段2和阶段3，确保执行引擎和 AI 功能稳定

### 选项 D：自定义
告诉我你的时间限制和优先级，我们定制方案

---

## 💡 额外建议

### Jarvis 语音助手
虽然 Jarvis 是 0% 覆盖率，但我建议**暂时降低优先级**：
- 理由1：语音功能依赖外部硬件和服务
- 理由2：测试难度高（需要音频数据集）
- 理由3：非核心业务逻辑
- 建议：在阶段4后再处理，或采用手动测试

### 测试文档
每个阶段完成后，自动生成：
- 测试覆盖率报告
- 测试用例清单
- 缺陷发现记录
- 性能基准报告

---

## ❓ 你的选择

请告诉我：
1. **你想选择哪个方案？** (A/B/C/D)
2. **你的时间限制是多少？** (天数)
3. **团队规模是多少？** (几个人)
4. **有没有必须先做的模块？** (特定需求)

我会根据你的选择立即开始实施！
