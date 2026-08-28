# 鎏灏 AI OS Y1.0 整改前基线检查报告

> 生成时间：2026-08-27
> 检查范围：D:\LiuHao-AI-OS 全量代码
> 检查原则：定位到具体代码行，不猜测，不修改

---

## 一、当前真实完成度

### 已完成（L3-L4，可直接使用）

| 模块 | 完成度 | 前端 | 后端 API | 数据库 | 测试 |
|------|--------|------|----------|--------|------|
| 权限系统（RBAC+ABAC+数据范围） | L3 | ✅ | ✅ | ✅ | 111 用例 |
| 认证系统 | L3 | ✅ | ✅ | ✅ | 集成测试 |
| AI Agent 调度 | L3 | ✅ | ✅ | ✅ | 有 |
| Workflow 引擎 | L3 | ✅ | ✅ | ✅ | 有 |
| 任务系统 | L3 | ✅ | ✅ | ✅ | 有 |
| 知识库 RAG | L3 | ✅ | ✅ | ✅ | 有 |
| CRM（Lead/客户画像） | L3 | ✅ | ✅ | ✅ | 有 |
| 独立站管理 | L3 | ✅ | ✅ | ✅ | 有 |
| SEO 工具 | L3 | ✅ | ✅ | ✅ | 有 |
| 供应商管理 | L3 | ✅ | ✅ | ✅ | 有 |
| 报价单管理 | L3 | ✅ | ✅ | ✅ | 有 |
| 审计系统 | L3 | ✅ | ✅ | ✅ | 有 |
| 数据导入 | L3 | ✅ | ✅ | ✅ | 有 |
| Dashboard 驾驶舱 | L3 | ✅ | ✅ | ✅ | 有 |
| 外贸业务模板 | L3 | ✅ | ✅ | ✅ | 有 |
| 多平台集成基础 | L2-L3 | ✅ | ✅ | ✅ | 有 |

### 部分完成（L2-L3，有代码但需打通）

| 模块 | 完成度 | 核心缺口 |
|------|--------|----------|
| 自动获客引擎 | L2-L3 | 海关数据需配置数据源，社媒爬虫受合规限制 |
| AI 元学习 | L2 | 无前端页面，学习结果未被自动使用 |
| 企业记忆 | L2 | 两套记忆系统未统一，未与 A gent 执行链路深度集成 |
| 成本追踪与预算 | L2-L3 | 无 ROI 计算，无预算分配优化 |
| 供应商风险分析 | L2-L3 | 部分链路依赖 Mock，Embedding 存储为 TODO |
| Dashboard 告警 | L2 | 仅系统级告警，无业务级告警和通知 |

### 未完成（L1-L2，严重缺口）

| 模块 | 完成度 | 说明 |
|------|--------|------|
| 老板目标中心 | L1 | 有后端解析代码，无前端入口 |
| AI 集体智能 | L1 | 跨 Agent 知识共享不存在 |
| 主动经营/异常检测 | L1 | 仅系统级告警 |
| 动态信任体系 | L1 | 能力评分返回 1.0 占位 |
| 失败恢复链 | L1 | 仅 Provider 重试 |
| 老板长期不在线 | L0 | 完全不存在 |
| 自我优化循环 | L1 | 仅元学习概念无闭环 |
| 预算与 ROI | L1-L2 | 有预算控制，无 ROI 计算 |

---

## 二、P0 问题（不解决无法正常使用）

### P0-1：6 个 productization 测试失败

**根因**：`tests/productization/` 目录下的测试因数据库模型变更或 API 响应格式变化而失败。
**文件**：`tests/productization/test_*.py`
**影响**：产品化链路不可靠，部署前无法通过完整测试套件。

### P0-2：Docker 部署链路不稳定

**根因分析**：
- **Dockerfile 启动命令**：`CMD ["uvicorn", "src.api.app:create_app", "--factory"]` — 正确使用 `create_app` 工厂函数（[Dockerfile:16](file:///d:/LiuHao-AI-OS/Dockerfile#L16)）
- **docker-compose.yml**：backend 使用 `build: .`，正确设置 `DATABASE_URL` 为 PostgreSQL（[docker-compose.yml:16](file:///d:/LiuHao-AI-OS/docker-compose.yml#L16)）
- **前端 nginx 代理**：`/api/` 路径代理到 `http://backend:8000`，配置正确（[nginx.conf:14](file:///d:/LiuHao-AI-OS/frontend/nginx.conf#L14)）
- **上次故障根因**：数据库密码认证失败，原因是 Docker volume 中残留旧密码，需要 `ALTER USER` 重置（已解决但仍需验证）
- **当前风险**：Docker Compose 未经过完整启动验证，上次启动后 frontend 到 backend 的连通性未确认

### P0-3：未配置真实 LLM Provider

**根因**：`.env.example` 中 `LLM_PROVIDER=mock` 默认使用 MockProvider（[app.py:95](file:///d:/LiuHao-AI-OS/src/api/app.py#L95)）
**文件**：`src/ai/providers.py:MockProvider` 返回预设响应
**影响**：所有 AI 功能返回假数据，无法产生真实业务结果

### P0-4：平台消息同步返回空列表

**根因**：WhatsAppProvider 和 FacebookProvider 的 `fetch_messages/fetch_contacts` 方法返回空列表（[providers.py](file:///d:/LiuHao-AI-OS/src/integrations/providers.py)）
**影响**：统一收件箱无数据，多平台经营不可用

---

## 三、P1 问题（核心产品能力缺口）

### P1-1：老板目标中心 — 无前端入口

**已存在**：
- [command_processor.py](file:///d:/LiuHao-AI-OS/src/ai/command_processor.py) — 目标解析（关键词匹配，非 LLM）
- [planner.py](file:///d:/LiuHao-AI-OS/src/ai/planner.py) — 模板化任务分解（4 个硬编码模板）
- [workflow_bridge.py](file:///d:/LiuHao-AI-OS/src/ai/workflow_bridge.py) — 计划→Workflow 转换

**缺失**：
- 前端目标输入页面（老板输入目标的入口）
- 目标持久化存储（无 Goal 数据库模型）
- 目标执行进度跟踪
- KPI 定义和跟踪
- 目标→预算的关联

### P1-2：自动获客引擎 — 数据源未打通

**已存在**：
- [engines.py](file:///d:/LiuHao-AI-OS/src/crm/engines.py) — 获客引擎代码
- API：`/api/v1/crm/acquisition/run`（[crm.py:267](file:///d:/LiuHao-AI-OS/src/api/routes/crm.py#L267)）

**缺失**：
- 真实海关数据源配置
- 社媒爬虫受合规限制（项目已明确禁止）
- 执行效果无数据源验证

### P1-3：失败恢复链 — 仅重试无恢复

**已存在**：
- Provider 层面指数退避重试（[providers.py:191](file:///d:/LiuHao-AI-OS/src/ai/providers.py#L191)）

**缺失**：
- 失败原因分类和分析
- 策略调整（更换 AI 员工/Provider/参数）
- 失败经验沉淀
- 超过安全阈值→请求老板

### P1-4：预算与 ROI — 无 ROI 计算

**已存在**：
- CostTracker 预算检查（[cost_tracker.py:170](file:///d:/LiuHao-AI-OS/src/ai/cost_tracker.py#L170)）
- 子账号预算设置 API（[accounts.py:475](file:///d:/LiuHao-AI-OS/src/api/routes/accounts.py#L475)）

**缺失**：
- ROI 计算模型
- 预算分配优化
- 低效投入→自动暂停
- 收益预测

---

## 四、P2 问题（重要增强）

| # | 问题 | 当前状态 | 关键文件 |
|---|------|----------|----------|
| P2-1 | AI 集体智能 | 不存在 | — |
| P2-2 | 主动经营/异常检测 | 仅系统级告警 | `ceo_dashboard_module.py` |
| P2-3 | 动态信任体系 | 能力评分占位 1.0 | `agent_router.py:148` |
| P2-4 | 自我优化循环 | 仅元学习概念 | `evolve/growth.py` |
| P2-5 | 语义搜索 | TODO 未实现 | `knowledge/retrieval.py` |
| P2-6 | PDF/DOCX/XLSX 解析 | TODO 占位 | `knowledge/processing.py` |
| P2-7 | 元学习前端页面 | 无 | — |
| P2-8 | 企业知识图谱前端 | 无 | — |
| P2-9 | 记忆管理前端 | 无 | — |
| P2-10 | 条件判断引擎 | Simple stub | `workflow/executor.py:363` |

---

## 五、Mock / Stub / TODO 清单

### 分类 A：仅测试允许存在

| 项目 | 文件 | 风险 |
|------|------|------|
| 测试中的 MockProvider | `tests/*` | 无 |

### 分类 B：开发环境允许存在

| 项目 | 文件 | 风险 |
|------|------|------|
| MockProvider（默认） | `src/ai/providers.py:582` | 开发环境假数据 |
| 翻译回退 Mock | `src/integrations/translation.py` | 翻译质量不可控 |
| Embedding Mock | `src/knowledge/embedding.py` | 向量搜索无真实结果 |

### 分类 C：生产环境禁止存在

| 项目 | 文件 | 风险 |
|------|------|------|
| 供应商风险分析 Mock | `src/business/supplier/risk_agent.py` | 返回假风险分析 |
| 外贸动作返回模拟结果 | `src/workflow/trade_actions.py:287` | 报价/审批/翻译不可用 |
| MLOps 模拟 | `src/mlops/*` | 非真实 ML 训练 |
| Dashboard 演示活动数据 | `frontend/DashboardPage.tsx` | 显示假活动 |

### 分类 D：必须替换为真实实现

| 项目 | 文件 | 行号 |
|------|------|------|
| 能力评分 1.0 占位 | `src/ai/agent_router.py` | L148 |
| 审批流程未完成 | `src/ai/tools.py` | 注释 |
| 供应商 Embedding TODO | `src/business/supplier/risk_agent.py` | L672 |
| 语义搜索 TODO | `src/knowledge/retrieval.py` | — |
| 文档解析 TODO | `src/knowledge/processing.py` | — |
| 条件判断 Stub | `src/workflow/executor.py` | L363 |
| WhatsApp/Facebook 消息为空 | `src/integrations/providers.py` | — |

---

## 六、登录问题根因

### 根因 1：登录错误信息未区分类型

**代码**：[auth.py:197](file:///d:/LiuHao-AI-OS/src/api/routes/auth.py#L197)
```python
if not user or not verify_password(login_data.password, user.hashed_password):
    raise HTTPException(status_code=401, detail="Invalid username or password")
```
**问题**：账号不存在 和 密码错误 返回相同信息，前端无法区分。

### 根因 2：无 Refresh Token 机制

**代码**：[auth.py:31](file:///d:/LiuHao-AI-OS/src/identity/auth.py#L31)
```python
def create_access_token(data: dict) -> str:
    # 只生成 access token，无 refresh token
```
**问题**：Token 过期后无法自动刷新，需要用户重新登录。

### 根因 3：前端 API Base URL 与后端端口不一致

**代码**：[frontend/.env:4](file:///d:/LiuHao-AI-OS/frontend/.env#L4)
```
VITE_API_BASE=http://localhost:8001
```
**问题**：后端实际端口是 8000（[docker-compose.yml:12](file:///d:/LiuHao-AI-OS/docker-compose.yml#L12)），但前端开发环境配置为 8001。**这是"网络连接异常"的核心原因之一。**

### 根因 4：开发环境 CORS 配置正确但无端口限制

**代码**：[app.py:380](file:///d:/LiuHao-AI-OS/src/api/app.py#L380)
```python
allow_origins=["*"]
```
**问题**：无限制的 CORS 在生产环境存在安全隐患，但开发环境不是问题。

### 根因 5：前端 Token 仅存 localStorage

**代码**：[auth.ts:13](file:///d:/LiuHao-AI-OS/frontend/src/services/auth.ts#L13)
**问题**：localStorage 在无痕模式/隐私模式下可能不可用，导致登录后无法保持会话。

---

## 七、子账号审批问题根因

### 链路确认：完整且正确

| 步骤 | 代码 | 行号 | 状态 |
|------|------|------|------|
| 子账号注册 | `auth.py:register_sub_account` | L55 | ✅ 正确设置 tenant_id, parent_user_id, approval_status="pending" |
| 主账号查询审批 | `accounts.py:pending-approvals` | L218 | ✅ 正确按 parent_user_id 过滤 |
| 审批通过 | `accounts.py:approve` | L240 | ✅ 设置 approval_status=APPROVED, is_active=True |
| 审批拒绝 | `accounts.py:reject` | L297 | ✅ 设置 approval_status=REJECTED, is_active=False |
| 登录拦截 | `auth.py:login` | L215-232 | ✅ 不同状态返回不同 403 错误 |
| 数据范围 | `visibility.py:DataScopeFilter` | — | ✅ 完整实现 |

**结论**：子账号审批链路完整正确，无根因问题。可能的故障点在于：
1. 前端 `fetchPendingApprovals` 未正确传递 token
2. 审批页面未自动刷新列表

---

## 八、Docker/后端启动问题根因

### 根因 1：前端开发环境端口配置错误

**问题**：`VITE_API_BASE=http://localhost:8001`（[frontend/.env:4](file:///d:/LiuHao-AI-OS/frontend/.env#L4)）
后端实际端口是 8000。开发模式下前端从 8001 请求 API 会失败。
**Docker 生产模式下**：前端 nginx 代理 `/api/` → `backend:8000`，此问题不存在。
**本地开发模式下**：此配置导致"网络连接异常"。

### 根因 2：Docker Compose 执行路径问题

**问题**：`docker-compose.yml` 在项目根目录 `D:\LiuHao-AI-OS\`，需从该目录执行 `docker compose up -d`。

### 根因 3：数据库密码认证残留

**问题**：Docker volume 中残留旧密码，首次启动可能失败。已在 `docker-compose.yml` 中通过 `POSTGRES_PASSWORD` 环境变量设置密码。

### 启动入口确认

**Dockerfile**：[Dockerfile:16](file:///d:/LiuHao-AI-OS/Dockerfile#L16)
```
CMD ["uvicorn", "src.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```
**正确性**：`create_app` 是工厂函数（[app.py:367](file:///d:/LiuHao-AI-OS/src/api/app.py#L367)），`--factory` 参数正确。

---

## 九、老板目标中心缺口

### 已存在（可复用）

| 组件 | 文件 | 说明 |
|------|------|------|
| CEOCommandProcessor | `src/ai/command_processor.py` | 目标解析，关键词匹配 |
| IntelligentPlanner | `src/ai/planner.py` | 4 个模板的任务分解 |
| WorkflowBridge | `src/ai/workflow_bridge.py` | 计划→Workflow 转换 |
| AIOrchestrator | `src/ai/orchestrator.py` | 多 Agent 编排 |
| AgentRuntime | `src/ai/agents.py` | Agent 执行 |
| ToolRegistry | `src/ai/tools.py` | 工具注册与执行 |
| CostTracker | `src/ai/cost_tracker.py` | 成本追踪 |
| Workflow templates | `src/workflow/trade_templates.py` | 外贸业务模板 |

### 缺失（需新建）

| 组件 | 说明 |
|------|------|
| **Goal 数据库模型** | 持久化存储目标、KPI、进度、预算 |
| **Goal 前端页面** | 老板输入目标的口，显示进度/结果 |
| **Goal→Plan 完整链路** | 目标解析→LLM 补充上下文→可执行性判断→计划生成 |
| **目标执行监控** | 实时进度、AI 员工状态、异常告警 |
| **目标完成报告** | ROI、成本、成功率、失败原因、下一步建议 |

---

## 十、自主经营闭环缺口

### 当前链路（部分存在）

```
Owner Goal  →  Goal Parser  →  Planner  →  Workforce Selection
     ↓
Execution Plan  →  Workflow  →  Task  →  Tool  →  Business Result
     ↓
Monitoring  →  [Evaluation  →  Failure Analysis  →  Strategy Adjustment  →  Retry]
```

### 断点位置

| 链路步骤 | 当前状态 | 缺失 |
|----------|----------|------|
| Owner Goal → Goal Parser | L1 无前端入口 | 前端输入页面 |
| Goal Parser | L2 关键词匹配 | 需升级为 LLM 解析 |
| Execution Plan | L2 模板化 | 需动态生成 |
| Workforce Selection | L2 存在 | 需匹配目标→选择 AI 员工 |
| Workflow → Task | L3 存在 | 需完善 |
| Business Result | L2 部分 Mock | 需真实数据 |
| **Monitoring → Evaluation** | **L1 不存在** | **评估环节缺失** |
| **Failure Analysis** | **L1 不存在** | **失败分析缺失** |
| **Strategy Adjustment** | **L1 不存在** | **策略调整缺失** |
| **Retry/Re-plan** | **L1 仅重试** | **完整恢复链缺失** |
| **ROI** | **L1 不存在** | **ROI 计算缺失** |
| **Memory → Learning** | **L1 未集成** | **经验沉淀缺失** |

---

## 十一、最终整改执行顺序

### 第 1 步：修复现有问题（P0）

1. 修复 frontend `.env` 端口配置（8001→8000）
2. 确认 Docker 部署链路完整可用
3. 修复 6 个 productization 测试失败
4. 配置真实 LLM Provider

### 第 2 步：构建老板目标中心（P1）

5. 创建 Goal 数据库模型
6. 创建 Goal 前端页面（目标输入 + 进度视图）
7. 创建 Goal API（创建/查看/跟踪）
8. 连接 Goal → Parser → Planner → Workflow 完整链路
9. 添加目标执行监控（进度/AI 员工状态/异常）

### 第 3 步：构建失败恢复链（P1）

10. 创建失败原因分类和分析
11. 创建策略调整机制（更换 AI 员工/Provider/参数）
12. 创建失败经验沉淀
13. 创建安全阈值→请求老板机制

### 第 4 步：构建经营闭环（P1-P2）

14. 创建 ROI 计算模型
15. 创建评估环节（执行→评估→发现问题）
16. 连接 Memory 沉淀经验
17. 创建主动经营/异常检测（业务级告警）

### 第 5 步：AI 集体智能（P2）

18. 创建跨 Agent 知识共享机制
19. 创建动态信任评分

### 第 6 步：长期能力（P3）

20. 老板长期不在线模式
21. 自我优化循环
22. 生产环境加固

---

## 十二、测试验收清单

整改完成后必须验证以下 25 项：

| # | 验收项 | 验证方式 |
|---|--------|----------|
| 1 | 登录 | 前端表单 + API |
| 2 | 密码错误提示 | 明确"密码错误" |
| 3 | 账号不存在提示 | 明确"账号不存在" |
| 4 | 网络异常提示 | 明确"网络异常" |
| 5 | 子账号注册 | 前端表单 + API |
| 6 | 主账号看到审批 | 审批列表 |
| 7 | 主账号批准 | 审批通过 API |
| 8 | 子账号登录 | 引导到子账号门户 |
| 9 | RBAC 权限检查 | 测试用例 |
| 10 | 数据范围过滤 | 测试用例 |
| 11 | 老板目标输入 | 前端页面 |
| 12 | 目标→计划分解 | API |
| 13 | 计划→Agent 路由 | 日志 |
| 14 | Agent 执行 | 日志 |
| 15 | Workflow 执行 | 日志 |
| 16 | 失败恢复 | 模拟失败→自动恢复 |
| 17 | 预算控制 | 超预算拦截 |
| 18 | 审计日志 | 查询审计 |
| 19 | Docker 启动 | `docker compose up -d` |
| 20 | 前端→后端连通 | 浏览器访问 |
| 21 | 后端→数据库连通 | 健康检查 |
| 22 | 子账号数据隔离 | 不同子账号数据不交叉 |
| 23 | 跨租户隔离 | 不同租户数据不交叉 |
| 24 | 全部测试通过 | `pytest` |
| 25 | 无 Mock 响应 | 配置真实 Provider 后验证 |