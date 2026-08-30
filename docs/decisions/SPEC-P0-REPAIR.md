# Spec - 鎏灏 AI OS P0 修复工程 v1.0.0

> 生成日期：2026-08-30
> 基于：《鎏灏 AI OS Y1.0 总蓝图》+ 《docs/鎏灏AI_OS_总蓝图差距报告.md》（实测审计）
> 状态：已确认（用户已拍板"按你的来走"）
> 工程类型：**修复型工程（非新功能开发）** —— 严守"修复现有问题 → 打通现有模块"，禁止重构、禁止删功能、禁止新增 Phase

---

## 1. 产品定义

- **一句话描述**：修复导致鎏灏 AI OS 完全不可用的 3 个 P0 阻断缺陷，并修复主干测试，使系统恢复"能登录、能跑通真实经营闭环"的可用状态。
- **目标用户**：项目开发者与老板（最终用户）
- **核心问题**：登录 100% 失败（schema 漂移 13 列）、知识库上传 500（16 处审计签名断裂）、0 名 AI 员工可执行（Provider 错配）

## 2. MVP 范围（锁定——不在此列表的一律不做）

| 优先级 | 任务 | 验收标准摘要 |
|--------|------|-------------|
| P0-A | **Alembic 真迁移替换过期硬编码字典** | 新迁移文件补齐 13 列；`alembic upgrade head` 后 dev.db schema 与 ORM 完全一致；登录返回 200 |
| P0-B | **修复 16 处 AuditService.log 旧签名调用** | 知识库文档上传返回非 500；`grep` 全库无缺 session/status 的审计调用；lifecycle 3 处补 `await` |
| P0-C | **UpdateEmployeeRequest 增加 provider_config 字段** | PATCH 员工可更新 provider_config 并落库 |
| P0-D | **重建 AI 员工编制并绑定 Ollama** | 5 部门齐备且在岗；全员 `provider_config={"provider":"ollama"}` |
| P0-E | **补全 requirements.txt** | 全新 venv 安装后 `from src.api.app import create_app` 成功 |
| P2-A | **修复 20 个失败主干测试** | 全量 pytest 0 failed（693 collected） |

## 3. 明确不做（Out-of-Scope — 锁定）

| 不做的功能 | 原因 | 何时考虑 |
|------------|------|----------|
| 清除获客 SAMPLE 假数据 / 接真实数据源 | 属第三波（P1） | 本轮验收后 |
| 绩效/成本落库改造（内存 dict→DB） | 属 P1 | 本轮验收后 |
| embedding 切真模型 | 属 P1 | 本轮验收后 |
| CRM 画像/评分/预测 | 属 P1 | 本轮验收后 |
| 任何 UI 改动 | 前端链路未坏 | 最后优化 UI 阶段 |
| 大规模重构 / 删除现有功能 / 改产品定位 | 用户明令禁止 | — |

## 4. 技术架构（锁定——沿用现有栈，不换）

| 层 | 技术 | 版本 | 说明 |
|----|------|------|------|
| 后端 | FastAPI | 已安装 | 不动 |
| ORM | SQLAlchemy 2.x async | 已安装 | 不动 |
| 迁移 | Alembic | 需补入 requirements | **本次修复核心工具** |
| 数据库 | SQLite（dev.db） | - | 修复而非重建 |
| LLM | Ollama qwen2.5:3b | 本机已运行 | 员工统一绑定 |
| 测试 | pytest | 8.x | 修 20 个失败 |

## 5. 数据库变更清单（锁定——P0-A）

**方式**：**双轨修复**（最小风险，实测已知 `init_database()` 在启动时执行该字典路径——dev.db 中 `approval_status`/`ai_budget_monthly` 正是它补的）：
1. **立即修复轨**：把 13 列全部补入 `src/api/dependencies/database.py:169` 的迁移字典 → 下次启动自动愈合 dev.db
2. **长期基线轨**：新增 Alembic 迁移（列存在性检查，幂等），`alembic stamp head` 对齐现有库，作为全新环境的建表基线

> ⚠️ Alembiz 陷阱：`alembic_version` 为空表且仅有 1 个 initial 迁移，直接 `upgrade head` 会在已存在的表上崩溃——必须先 `stamp` 或让迁移幂等。

补齐 13 列（列类型必须与 `src/` 对应 ORM 模型定义**逐一对齐**，开发前先读 ORM 确认精确类型，下表为审计实测可用的最小类型）：

| 表 | 列 | 建议类型 | ORM 定义位置 |
|----|----|----------|--------------|
| users | business_role | VARCHAR(30) | src/identity/models.py |
| users | data_scope | VARCHAR(20) | src/identity/models.py |
| users | permissions_config | JSON | src/identity/models.py |
| tasks | retry_count | INTEGER DEFAULT 0 | src/tasks/models.py |
| tasks | max_retries | INTEGER DEFAULT 3 | src/tasks/models.py |
| agent_memories | memory_level | VARCHAR(20) | src/ai/memory_store.py 或对应模型 |
| agent_memories | importance | FLOAT | 同上 |
| agent_memories | is_core | BOOLEAN | 同上 |
| agent_memories | expires_at | DATETIME | 同上 |
| agent_memories | last_accessed_at | DATETIME | 同上 |
| agent_memories | access_count | INTEGER | 同上 |
| leads | source_type | VARCHAR(30) | src/crm/models.py |
| platform_messages | source_type | VARCHAR(30) | src/integrations/models.py |

**数据库处置（用户已拍板）**：
- `dev.db`：执行迁移修复，保留现有数据
- `prod.db`：**废弃**。重命名为 `prod.db.archived-20260830` 留档（不删除），并在报告中注明
- `test.db` / `verify_e2e.db`：不动（测试自建自用）

**验收命令**：
```bash
# 重启应用后（init_database 自动愈合）或手动 alembic upgrade head
python -c "对比脚本：全量 ORM vs PRAGMA table_info，输出 0 缺失"
curl POST /api/v1/auth/login → 200 + access_token
```

## 6. 审计签名修复清单（锁定——P0-B）

**正确签名**（`src/identity/audit.py:223`）：
```python
await AuditService.log(
    session, action, resource_type, status,          # 4 个必填位置参数
    user_id=None, resource_id=None, details=None,
    error_message=None, ip_address=None, user_agent=None,
)
```

**需修复的 16 处**（全部改为传 `session=` 与 `status="success"`；`actor_id` 一律改为 `user_id`）：

| 文件 | 行号 | 额外注意 |
|------|------|----------|
| src/knowledge/documents.py | 272 | — |
| src/knowledge/documents.py | 323 | — |
| src/knowledge/documents.py | 402 | — |
| src/knowledge/documents.py | 461 | — |
| src/knowledge/documents.py | 597 | — |
| src/knowledge/enterprise_memory.py | 249 | — |
| src/knowledge/enterprise_memory.py | 269 | — |
| src/knowledge/memory.py | 427 | — |
| src/knowledge/retrieval.py | 475 | — |
| src/knowledge/retrieval.py | 709 | — |
| src/workforce/lifecycle.py | 112 | **补 `await`**（当前是同步调用异步函数，协程从未执行） |
| src/workforce/lifecycle.py | 182 | **补 `await`** + `actor_id`→`user_id` |
| src/workforce/lifecycle.py | 253 | **补 `await`** + `actor_id`→`user_id` |
| src/api/routes/ai_brain.py | 139 | — |
| src/api/routes/ai_brain.py | 184 | — |
| src/api/routes/ai_brain.py | 358 | — |

**验收**：知识库上传 txt 文档返回 201/200；`python` 扫描全库 0 处"含 action 但缺 session"的审计调用。

## 7. API 变更清单（锁定——P0-C）

| Method | Path | 变更 | 说明 |
|--------|------|------|------|
| PATCH | /workforce/employees/{id} | `UpdateEmployeeRequest` 增加 `provider_config: Optional[Dict[str, Any]] = None`，透传给 service 层 | service 层 `employee.py:510` 已支持该覆盖逻辑，仅补路由层透传 |

## 8. AI 员工编制（锁定——P0-D）

**目标编制**（按 AgentRouter 5 部门映射，`src/ai/agent_router.py:33`）：

| 部门 | 岗位 | 人数 | 来源 |
|------|------|------|------|
| ceo_office | ceo_assistant | 1 | 现有"鎏灏核心助理"重绑 |
| research | market_researcher | 1 | 激活"Gemini - Research Officer"并重绑 |
| research | product_researcher | 1 | 激活"Kimi - Chinese Research Officer"并重绑 |
| marketing | marketing_specialist | **1（新建）** | 全新建 |
| sales | sales_representative | 1 | 现有"金牌外贸销售"重绑 |
| sales | account_manager | 1 | 现有"AI 谈判专家"重绑 |
| operations | operations_coordinator | 1 | 现有"跨境运营顾问"重绑 |

**绑定规则**：全员 `provider_config = {"provider": "ollama", "model": "qwen2.5:3b"}`；`status=active`。

**数据落库方式**：用脚本或 SQL 直接更新 `ai_employees` 表（`config` 列存 provider_config JSON），并在迁移或 seed 脚本中固化，确保可重建。

## 9. 依赖补全清单（锁定——P0-E）

`requirements.txt` 追加（按实际 import 存在的）：
```
openai
anthropic
chromadb
sentence-transformers
edge-tts
pypdf
pdfplumber
Pillow
python-docx
pytesseract
alembic
bcrypt
greenlet
```
> `google-*`：确认 `src/ai/providers.py` 中 `google` import 的具体包名后补对应项。
> 逐项核对：**只加真实 import 的，不加想象中的**。

## 10. 测试修复范围（锁定——P2-A）

| 文件 | 数量 | 已知根因 |
|------|------|----------|
| tests/scheduler/test_business_scheduler.py | 8 | `SmartFakeGateway` 缺 `register_model`（app.py:270 演进后测试替身未同步） |
| tests/integration/test_p0_fixes.py | 7 | LLM 目标解析相关 |
| tests/integration/test_e2e_chain.py | 4 | E2E 经营链 |
| tests/api/test_memory_crud.py | 1 | viewer 权限 |

**原则**：修测试替身使其对齐真实代码路径，**禁止为了让测试变绿而弱化断言或 mock 掉被测逻辑**。

## 11. 验收标准（EARS 格式——QA 依此验收）

| 编号 | 验收标准 | 优先级 |
|------|----------|--------|
| AC-01 | When 用户提交合法登录凭证，系统**必须**返回 200 + access_token | P0 |
| AC-02 | When 老板提交自然语言目标（/goals/from-text），系统**必须**创建目标且 `parse_method` ∈ {llm, rule_based}，字段含 KPI/预算 | P0 |
| AC-03 | When 激活目标（/goals/{id}/activate），系统**必须**成功路由全部任务至在岗 AI 员工 | P0 |
| AC-04 | When 执行目标（/goals/{id}/execute），系统**必须**返回执行结果且 goal 进入终态，task_results 有真实输出 | P0 |
| AC-05 | When 上传 txt 文档至 /knowledge/documents，系统**必须**返回成功且 documents/document_chunks 落库 | P0 |
| AC-06 | When PATCH 员工带 provider_config，系统**必须**持久化该配置并下次执行生效 | P0 |
| AC-07 | When 全量运行 pytest，系统**必须** 0 failed（693 collected 基线） | P0 |
| AC-08 | If 在全新 venv 安装 requirements.txt 并 import src.api.app，系统**必须**成功 | P0 |
| AC-09 | Where provider 为 ollama 的员工执行任务，输出**必须**为真实 LLM 内容（非 mock 标记） | P0 |

## 12. 端到端验证步骤（最终门禁）

```bash
# 1. 迁移
alembic upgrade head

# 2. 启动
python -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8010

# 3. 登录（AC-01）
curl -X POST http://localhost:8010/api/v1/auth/login -H "Content-Type: application/json" \
  -d '{"username":"testuser2","password":"testpass123"}'
# 断言：200 + access_token

# 4. 建目标（AC-02）
curl -X POST http://localhost:8010/api/v1/goals/from-text -H "Authorization: Bearer $T" ...
# 断言：201 + parse_method

# 5. 激活（AC-03）→ 执行（AC-04）
# 断言：无 "No research AI employee available"、无 "Provider not registered"

# 6. 知识库上传（AC-05）
# 7. 员工 PATCH provider_config（AC-06）
# 8. 全量 pytest（AC-07）
```

## 13. 变更记录

| 日期 | 变更内容 | 原因 | 影响范围 |
|------|----------|------|----------|
| 2026-08-30 | 初版 | 基于 P0 差距审计 | 全部 P0 文件 |
