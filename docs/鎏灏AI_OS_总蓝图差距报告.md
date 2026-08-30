# 《鎏灏 AI OS 总蓝图差距报告》v2.0（P0 修复后复审）

> 审计对象：`D:\LiuHao-AI-OS`
> 审计日期：2026-08-30（第二轮复审，接续同日早间的 v1.0 审计）
> 审计方式：**只读审计 + 真实运行时验证**（未修改任何项目代码；运行时验证在 `dev.db` 的临时副本上完成，验证后已清理）
> 分级标准：**L1** 代码存在 / **L2** 能启动运行 / **L3** 能实际操作 / **L4** 能自主经营并产生真实业务结果
> 标记：✅ 已完成　🟡 部分完成　🔴 未完成　⚠️ 生产环境必须补强
> 基准：《鎏灏 AI OS Y1.0 总蓝图》十八章

---

## 0. 一句话结论（相对 v1.0 的变化）

> **v1.0 的结论是"造好了但没通电的机器"。本轮复审确认：P0 修复工程（`docs/decisions/SPEC-P0-REPAIR.md`）已落地，机器已通电——登录、知识库、目标理解、目标激活、目标执行、多 AI 员工真实 LLM 产出，本次审计全部实测跑通。**
> **引擎层已实测达到 L3**（完整闭环 completed，8 任务真实产出，工作流 COMPLETED）。
> 距离 L4（真实经营结果）的缺口现在集中在三层：**① 真实业务数据管道（获客/平台/海关/SEO 全为假数据或空凭据）；② 经营度量回写（KPI 进度、预算消耗恒为 0，老板看不到经营效果）；③ 经验持久化底座（绩效/成本存内存，信任评分因此退化为默认值）。**
> 下一步的关键词不是"修"，而是**"接真数据 + 记真账"**。

### 本轮决定性证据（全部为本次实测，非引用旧报告）

| 验证动作 | v1.0 结果 | **本轮结果** |
|---|---|---|
| 数据库 schema（users 19 列 / agent_memories 14 列） | 🔴 缺 13 列 | ✅ **全部补齐**，`alembic_version = b3c7d2e9a1f4`（P0 修复迁移已执行） |
| 登录 | 🔴 HTTP 500 | ✅ **200 + JWT**（boss 账号实测） |
| 知识库上传文档 | 🔴 HTTP 500 | ✅ **200，1 chunk 持久化落库** |
| 知识检索（关键词） | — | ✅ 返回刚上传的文档内容 |
| AI 员工 Provider 绑定 | 🔴 0 人可执行 | ✅ **11 人中 8 人 active 且绑定 ollama/qwen2.5:3b**，7 个部门齐备（含 research/marketing/analytics） |
| 自然语言建目标 | ✅（有质量缺陷） | ✅ `parse_method="llm"`，KPI 30 个 / 预算 1500 / 风险边界"不接触军事用途客户"全部正确抽取；时间 2026-12-31 正确；constraints 仍为分词碎片 |
| 目标激活 | 🔴 失败（无在岗员工） | ✅ **200，status=active，即时成功** |
| **目标执行（真实 LLM 全链路）** | 🔴 failed | ✅ **completed（7 分 25 秒）**，8 个任务全部 completed，`workflow_executions` 状态 COMPLETED，Kimi 研究官/金牌外贸销售/跨境运营顾问/核心助理等多名员工真实产出并落库 |
| 全量测试 | 🟡 673 通过 / 20 失败（全是核心闭环） | ✅ **692 通过 / 1 失败**（SPEC-P0-REPAIR 的"0 failed"目标基本达成，仅剩 1 个安全测试） |
| requirements.txt | 🔴 缺 15+ 依赖 | ✅ 已补全（P0-E 段落，逐文件标注 import 依据） |
| UpdateEmployeeRequest.provider_config | 🔴 不支持 | ✅ 已支持（workforce.py:80） |
| 生产库 prod.db | 🔴 同样缺列无法登录 | ⚠️ 已归档为 `prod.db.archived-20260830`（ADR-003），**尚无新生产库的建立/初始化流程** |

---

## 1. 二十项检查清单（本轮更新版）

### 1.1 已完成能力（实测可用）✅

| # | 能力 | 级别 | 证据 |
|---|---|---|---|
| 1 | 应用启动 + 健康检查 | L2 | `src.main:app` 启动成功，`/health/ready` 200，返回 scheduler/database 状态 |
| 2 | 登录 / JWT / bcrypt / 主子账号 | **L3** | boss 登录实测 200；`users.account_type` OWNER/SUB 模型完整 |
| 3 | 自然语言目标理解（真实 LLM） | **L3** | `parse_method="llm"`，KPI/预算/风险边界/时间全部正确抽取 |
| 4 | 目标 → 激活 → 执行 → 完成 | **L3** | **本次实测 completed，8 任务真实 LLM 产出，工作流 COMPLETED** |
| 5 | 知识库：上传 → 分块 → 持久化 → 检索 | **L3** | 上传 200 + chunk 落库 + 检索命中（P0-2 修复生效） |
| 6 | AI 员工组织（基础） | **L3** | 8/11 在岗绑定 Ollama；创建/激活/暂停/退休生命周期完整；`provider_config` 可覆盖 Provider/Model（ADR-002） |
| 7 | 失败恢复链 | **L3** | `recovery.py` 7 类策略 + `recovery_executor.py` 6 种动作（v1.0 实测产生过 2 条 failure_records 含经验沉淀） |
| 8 | 风险分级与审批治理 | L3 | `governance/risk.py` 外贸高风险操作清单；工具执行前真实创建审批单 |
| 9 | 真实 LLM Provider（Ollama） | L3 | `provider/status`：ollama/qwen2.5:3b available=true |
| 10 | 数据库迁移基线 | L2 | Alembic 双轨制（ADR-001）：`init_database()` 自愈字典 + 幂等迁移 `b3c7d2e9a1f4` |
| 11 | Docker 编排 | L2 | compose 密钥强制校验 + 健康检查；Dockerfile 用 `create_app --factory`（正确） |
| 12 | 敏感文件管理 | ✅ | `.env`/`.env.production` 不入库 |

### 1.2 部分完成能力 🟡

| 能力 | 缺口 | 证据 |
|---|---|---|
| **AI 员工组织** | 11 人中 3 人仍卡在 `created`（绑 deepseek/xai/openai 且无 Key）；无"外部 AI 员工"概念（is_external）；技能非一等公民（散落 metadata）；无 AI 管 AI 层级（manager_id） | dev.db 实测 |
| **知识库 RAG** | 持久化链路已通，但 **embedding 仍走 mock**（`config.py:73` 默认 mock，`.env` 无 `EMBEDDING_PROVIDER`）→ 语义检索无意义，当前仅关键词检索有效 | 实测 + 代码 |
| **LLM 解析质量** | constraints 退化为分词碎片（本次复现：`["工业阀门","30","1500","国","商",...]`） | 实测返回体 |
| **权限体系** | `require_permission` 真实 fail-closed，但 **viewer 越权写企业记忆被放行**（唯一红测试）；`roles`/`permissions`/`role_permissions` 三表 0 行，UI 改角色无实际效果 | pytest 失败详情 + dev.db |
| **动态信任体系** | `agent_router.py` 三维评分（能力/风险/信任）计算逻辑真实存在，但数据源（绩效记录）为空 → 分数退化为默认常量 | 代码 + employee_performance=0 行 |
| **自我学习** | 机制真实（failure_records/meta_knowledge），但 dev.db 中 failure_records=0、evolution_proposals=3 无人消费 | dev.db |
| **老板汇报** | `ceo_dashboard_module.py` 驾驶舱 693 行 + `generate_summary_report` 存在，但报告仅 4 项（蓝图要求 13 项）；异常扫描仅 3 类（线索下降/客户流失/供应商高风险，蓝图列 10 类） | 代码 |
| **供应商管理** | `routes/supplier.py` 15 端点齐全（CRUD/advanced-search/import/export/risk-history/contacts/certificates），但 AI 分析部分写死 80.0 分，且**前端零引用**（advanced-search/risk-history 全无调用） | grep 实证 |

### 1.3 只有框架、没有真正实现 🔴

| 能力 | 实况 |
|---|---|
| **预算与 ROI** | `src/cost/` 仅 31 行；无预算表；**本次实测：目标 completed 但 `budget_spent=0.0`——真实 LLM 花费完全没有记账**；无 ROI 计算/预测/超预算暂停 |
| **KPI 进度回写** | 本次实测：目标 completed 但 `kpi_current=0.0`——任务完成 ≠ KPI 更新，老板看不到"30 个客户完成了几个" |
| 绩效/成本持久化 | `workforce/performance.py`、`cost.py` 全部存内存 dict（`self._records`），进程重启即清零；`employee_performance`/`employee_costs` 表恒 0 行 |
| 多平台经营 | `integrations/providers.py` 9 处 `fetch_messages`/`fetch_contacts` 全部 `return []`；8 个平台账号凭据全空；`_MOCK_REPLIES` 伪造对方回信写入消息表 |
| 自动获客（三条路线） | `crm/engines.py` SOCIAL/GOOGLE/CUSTOMS 三组 SAMPLE 共 9 家编造客户无条件返回；`leads` 表 20 行 = SAMPLE 复制两遍；`crm.py:581` 假海关数据标 `source="customs-api"`（来源欺诈） |
| 独立站 + SEO | `site_os/seo.py` 用 `random.randint`/`random.choice` 生成搜索量与 Google 排名；无真实 GA/GSC 接入；无真实发布能力 |
| 客户画像 / 评分 / 成交预测 / 复购 | `src/crm/` 内 grep 零命中（画像/复购）；仅历史胜率统计，无预测模型 |
| 主动经营 | `SCHEDULER_ENABLED=false`（启动日志确认 `scheduler_disabled_by_config`）；无通知渠道 |
| ABAC | `security/abac.py` 23 行，硬编码字符串判定，玩具级 |
| MLOps / SRE / 可观测性 | 7 文件 289 行 / 1 文件 / 4 文件 71 行，均为占位骨架 |
| Webhook 安全 | 无 HMAC 签名校验（grep hmac/signature 零命中） |

### 1.4 前端有页面但后端没真正打通 🔴

| 页面 | 实况 |
|---|---|
| SEOPage | 后端返回的是随机数生成的假排名/假流量 |
| PlatformPage | 后端凭据全空，发送后系统自动伪造对方回信 |
| LeadsPage | API 可用（CRUD 真实），但库里 20 条全是编造 SAMPLE 数据 |
| ModelsPage / MetricsPage | 部分指标来自 `providers_metrics.py` 的 `random.uniform` 伪造延迟/成功率 |

### 1.5 后端有代码但前端没有入口 🟡

| 后端能力 | 前端 |
|---|---|
| `routes/supplier.py` 全套 15 端点（advanced-search / risk-history / contacts / certificates / batch / import / export） | **前端零引用**（前端只走 `/crm/suppliers/*` 另一套） |
| `routes/webhooks.py` | 无 UI |
| 老板离线经营报告（generate_summary_report） | 仅 4 项，无完整报告页面消费 |

### 1.6 Mock / 假数据清单（全部实测仍在）

| 位置 | 伪造内容 |
|---|---|
| `src/providers/mock.py` | `embeddings()` 恒返回 `[0.1,0.2,0.3]`（任意文本同一向量） |
| `src/crm/engines.py:32/71/108/256` | 三组客户 SAMPLE + 供应商 SAMPLE，无条件返回 |
| `src/api/routes/crm.py:581` | 假海关数据标注真实来源 `customs-api` |
| `src/site_os/seo.py:76-77/288-290` | 随机数生成搜索量/难度/排名 |
| `src/business/supplier/risk_agent.py:328-332` | 写死 `overall_score: 80.0` 冒充 AI 评估 |
| `src/integrations/service.py:38/289` | `_MOCK_REPLIES` 随机伪造"对方回复" |
| `src/api/providers_metrics.py:118` | `random.uniform` 伪造延迟/成功率 |

### 1.7 TODO / Stub

`src/integrations/providers.py` 四个真实 Provider 的 `fetch_messages()` 全部 `return []`；`workflow/executor.py:959` `_evaluate_condition` 仍为简单 stub（工作流条件判断未实现）。

### 1.8 未接入的外部 API / AI

- **外部 API**：Google Custom Search、海关数据商、1688/企查查、Facebook Graph、LinkedIn、WhatsApp Cloud、企业微信、Google Analytics / Search Console——凭据全部为空，0 个真实可用。
- **AI**：openai/anthropic/google/deepseek/moonshot/xai 六个境外 Provider 无 Key（当前全员绑 Ollama，可用但不依赖境外 Key）。

### 1.9 数据库链路 ✅（v1.0 P0 已修复）

- 13 个缺失列已通过 Alembic 迁移 `b3c7d2e9a1f4_p0_repair_add_missing_columns.py` 补齐；dev.db 已 stamp 到该版本。
- `init_database()` 自愈字典与 Alembic 双轨并存（ADR-001 有明确说明）。
- ⚠️ 遗留：根目录仍散落 `dev.db` / `test.db` / `verify_e2e.db`（0 表空壳）/ `prod.db.archived-20260830` 四个库文件，无统一库管理约定。
- ⚠️ **生产库重建流程缺失**：prod.db 已废弃归档，但"新生产环境如何初始化（alembic upgrade head？init_database？）"无文档无脚本。

### 1.10 Workflow 链路 ✅（v1.0 P0 已修复）

本次实测：目标执行 → 8 任务全部 completed，`workflow_executions.status=COMPLETED`，result_data 真实落库。

### 1.11 权限 / 登录 / 主子账号

- ✅ 登录完全恢复（实测 200 + JWT）。
- 🔴 **新发现（唯一红测试）**：viewer 角色写企业记忆 `/api/v1/memory/business` 期望 403 实际 **200——越权写入被放行**（`tests/api/test_memory_crud.py::test_viewer_read_ok_write_forbidden`）。这是权限体系上的一个 fail-open 缺口。
- 🟡 `roles`/`permissions`/`role_permissions` 三表 0 行，真实鉴权走 RoleEnum 枚举——三张表 + `/roles` `/permissions` 路由仍是摆设。
- ⚠️ `get_token.py` 仍在根目录，硬编码 `testuser2/testpass123`。
- ⚠️ 无登录限流、无 refresh token、登录错误不区分账号不存在/密码错误、CORS `*`。

### 1.12 网络 / 后端启动 🟡（新发现）

- 🔴 **`scripts/start_api.sh` 与 README 的启动命令是错的**：两者都写 `uvicorn src.api.app:app`，但 `src/api/app.py` 只有 `create_app()` 工厂，**没有模块级 `app` 对象**——实测报 `Attribute "app" not found in module "src.api.app"`。正确入口是 `src.main:app`（`src/main.py:28`）或 Dockerfile 用的 `src.api.app:create_app --factory`。**按 README 操作的新开发者/运维必然启动失败。**
- ⚠️ `Settings` 要求 SECRET_KEY/JWT_SECRET_KEY ≥32 字符（安全上正确），但 README 未提及，密钥过短会直接 pydantic 校验崩溃（本轮测试首跑 188 个假失败即因此）。

### 1.13 Docker / 部署 🟡

- ✅ Dockerfile CMD 正确（`create_app --factory`）；compose 密钥强制校验、健康检查、nginx 反代正确。
- 🟡 Dockerfile 无 `alembic upgrade head`（依赖启动时自愈字典，ADR-001 已说明为有意设计，可接受但需知悉）。
- 🟡 `frontend/Dockerfile` 未先复制 `package-lock.json`（构建不可复现）。
- ⚠️ 生产库初始化流程缺失（见 1.9）。

### 1.14 测试 ✅（大幅改善）

**692 通过 / 1 失败（21 分 28 秒）**。v1.0 失败的 20 个核心闭环测试（scheduler 8 / p0_fixes 7 / e2e_chain 4 / memory_crud 1）中 **19 个已修复**，仅剩：

| 失败测试 | 原因 | 定级 |
|---|---|---|
| `test_memory_crud.py::test_viewer_read_ok_write_forbidden` | viewer 越权写企业记忆返回 200 而非 403 | **P1 安全缺陷** |

### 1.15 生产环境风险 ⚠️

1. 无监控告警、无备份调度验证、无生产库重建流程。
2. `SCHEDULER_ENABLED=false`——"老板不在线持续经营"未启用。
3. embedding 默认 mock 无生产防护（MockProvider 的 chat 有 `APP_ENV=production` 保护，embedding 没有）。
4. Webhook 无 HMAC 签名校验。
5. LLM=qwen2.5:3b 小模型：时间推理弱、constraints 碎片化（本次复现）。
6. viewer 越权写缺口（见 1.11）。

---

## 2. 蓝图十八章对照总表

| 蓝图章节 | v1.0 | **本轮** | 关键缺口 |
|---|---|---|---|
| 一、老板目标中心 | 🟡 | **✅ L3** | 解析/激活/执行全通；**缺 KPI 进度回写与预算记账** |
| 二、AI 员工组织 | 🟡 | **🟡 L3** | 8/11 在岗；3 人未激活；缺外部员工/技能/层级/AI 管 AI |
| 三、外贸核心业务 | 🔴 | **🔴 L1-L2** | 获客 0 条真实路线；CRM 缺画像/评分/预测/复购；供应商分析写死分数 |
| 四、多平台经营 | 🔴 | **🔴 L1** | 凭据空、fetch 全空、伪造回信 |
| 五、独立站 + SEO | 🔴 | **🔴 L1** | 随机数数据、无真实发布/排名/GA/GSC |
| 六、企业知识与记忆 | 🟡 | **🟡 L3** | 上传/分块/检索持久化已通；embedding mock；企业大脑空 |
| 七、AI 集体智能 | 🟡 | **🟡 L2** | 经验存取代码真实；绩效不落库 → 集体智能无数据底座 |
| 八、自我学习 | 🟡 | **🟡 L2** | 失败经验机制真实但库内为 0；无渠道/ROI 经验沉淀 |
| 九、自我优化 | 🟡 | **🟡 L2** | 恢复链真实；evolution_proposals 无人消费；治理边界有审批机制 ✅ |
| 十、主动经营 | 🔴 | **🔴 L1** | 调度器关闭；异常扫描仅 3/10 类；无通知渠道 |
| 十一、预算与 ROI | 🔴 | **🔴 L1** | **实测 budget_spent=0：真实 LLM 花费不记账**；无预算分配/监控/暂停 |
| 十二、动态信任体系 | 🔴 | **🟡 L2** | 三维评分逻辑真实；数据源空 → 退化为默认值；无升降权状态机 |
| 十三、老板长期不在线 | 🟡 | **🟡 L2** | 调度器代码真实默认关闭；离线报告仅 4/13 项 |
| 十四、失败恢复 | 🟡 | **✅ L3** | 7 策略 + 6 动作 + 经验沉淀，实测有效 |
| 十五、安全与治理 | 🟡 | **🟡 L2-L3** | RBAC/审计/PII 真实；viewer fail-open 缺口；角色表摆设；webhook 无签名 |
| 十六~十八、工程对照/验收标准/任务要求 | — | **✅ 审计本身** | 本报告即交付物 |

---

## 3. 优先级排序（P0 → P3）

### P0 —— 不解决则无法正常使用

**本轮结论：无新增 P0。上一轮 5 个 P0 已全部修复并经本次实测验证。**

（唯一接近 P0 的是 1.12 的启动文档错误——按 README 启动必失败，但因存在正确入口 `src.main:app` 且 Docker 路径正确，定为 P1 首位。）

### P1 —— 核心产品能力（1-3 周）

| # | 事项 | 依据 |
|---|---|---|
| P1-1 | **修复启动文档**：`scripts/start_api.sh` 与 README 改为 `src.main:app`（或 `create_app --factory`）；README 补"密钥≥32字符"说明 | 1.12 实测复现 |
| P1-2 | **修复 viewer 越权写企业记忆**（唯一红测试，安全 fail-open） | 1.11/1.14 |
| P1-3 | **KPI 进度回写 + 预算记账**：目标执行后 kpi_current/budget_spent 恒 0，老板看不到经营效果——这是"目标中心"从 L3 到 L4 的关键一步 | 本次实测 |
| P1-4 | **绩效/成本落库**：`performance.py`/`cost.py` 从内存 dict 改 DB；这也是信任评分、ROI、集体智能的公共数据底座 | 1.3 |
| P1-5 | **启用真实 embedding**：`.env` 设 `EMBEDDING_PROVIDER`（Ollama `nomic-embed-text` 等），替换恒 `[0.1,0.2,0.3]` 的 mock；给 embedding 加生产防护 | 1.2/1.15 |
| P1-6 | **打通第一条真实获客路线**（按既定决策：海关手动导入 → 付费 API）；清除 SAMPLE 假数据与 `source="customs-api"` 来源欺诈 | 1.3/1.6 |
| P1-7 | **多平台打穿第一条**（按既定决策顺序：WhatsApp → 企微 → 邮件）：配置真实凭据、实现真实 fetch、移除伪造回信 | 1.3 |
| P1-8 | 激活剩余 3 名 `created` 员工或明确裁撤；清理 `get_token.py` 硬编码凭据 | 1.2/1.11 |
| P1-9 | LLM 解析质量：prompt 注入当前日期修复时间幻觉；constraints 输出结构化 | 1.2 |

### P2 —— 重要增强（1-2 月）

| # | 事项 |
|---|---|
| P2-1 | 启用 Scheduler（SCHEDULER_ENABLED=true），实现主动经营巡检扩展到 10 类 + 通知渠道 |
| P2-2 | 老板离线经营报告补齐到 13 项 + 前端报告页消费 |
| P2-3 | CRM 四大缺口：客户画像 / 客户评分 / 成交预测 / 复购 |
| P2-4 | 供应商 15 端点接前端（SupplierAnalysisPage 升级），清理 risk_agent 写死 80 分 |
| P2-5 | SEO/独立站接真实数据（GA/GSC、真实排名抓取、真实发布） |
| P2-6 | 动态信任体系：基于落库绩效驱动升降权状态机 |
| P2-7 | 权限收口：角色表真实生效或下线摆设路由；webhook 补 HMAC；CORS 收紧；登录限流 + refresh token |
| P2-8 | 工作流条件判断（_evaluate_condition stub）真实实现 |
| P2-9 | 生产库初始化流程文档化（alembic upgrade head 路径） |

### P3 —— 后续优化

- ABAC 重写（现为 23 行玩具）、MLOps 真实流水线、SRE 备份容灾、可观测性接入
- AI 员工组织进阶：外部员工、技能一等公民、AI 管 AI 层级
- 清理根目录散落的 4 个 SQLite 库，统一库管理约定
- Jarvis 语音（791 行，蓝图未要求）
- 前端 MetricsPage 假指标清理（providers_metrics random）

---

## 4. 修复顺序建议（严格遵循第五步原则）

```
第 1 步  修 P1-1/P1-2（启动文档 + 越权缺口）——半天
第 2 步  记真账：P1-3/P1-4（KPI 回写 + 预算/绩效落库）——这是所有"经营能力"的公共地基
第 3 步  接真智能：P1-5（真实 embedding → RAG 语义检索生效）
第 4 步  接真数据：P1-6/P1-7（海关 → WhatsApp，按既定决策顺序）
第 5 步  做真实业务闭环：目标 → 获客 → 跟进 → 报价 → 成交，一条链路走通
第 6 步  最后优化 UI 与 P2/P3 增强
```

**明确不要做的事**（与 v1.0 相同，继续有效）：
- ❌ 不要大规模重构——引擎已实测能跑通完整闭环，架构是对的
- ❌ 不要删除现有功能、不改变"AI 经营合伙人"定位、不新增 Phase
- ❌ **不要为了跑通测试/演示而把真实业务换成 Mock——方向是去 mock**（当前 mock 清单见 1.6）

---

## 5. 结论：现在的鎏灏距离"AI 经营合伙人"还有多少距离

| 层 | v1.0 | **本轮** | 说明 |
|---|---|---|---|
| **基础设施层**（启动/登录/Schema/依赖） | 🔴 L1-L2（登录 500） | **✅ L2-L3** | 全部实测恢复 |
| **引擎层**（目标→规划→路由→执行→恢复） | 🟡 L3 可达（仅隔离库验证过） | **✅ L3 实测达成** | 本次审计在 dev.db 副本上完整跑通 completed 闭环，8 任务真实 LLM 产出 |
| **经营度量层**（KPI/预算/ROI/绩效/信任） | 🔴 L1 | **🔴 L1** | 记账链路缺失：执行完成但 kpi_current=0、budget_spent=0、绩效在内存——**老板看不到"经营得怎么样"** |
| **业务真实数据层**（获客/平台/海关/SEO/供应商） | 🔴 L1 | **🔴 L1** | 三条获客路线 0 条可用、平台凭据全空、SEO 随机数、20 条线索全是编的 |

**量化：距离 L4 约剩 50% 缺口，且缺口性质已从"修 bug"（v1.0 的 3 个 P0）转变为"接真数据 + 记真账"。**

引擎已经证明它能跑；下一步要让跑出来的结果**可见（KPI/预算回写）、可积累（绩效落库）、可变现（真实获客渠道）**。按 P1 顺序推进，第一步（P1-1/P1-2）半天可完成；P1-3/P1-4 完成后"老板目标中心"和"预算与 ROI"两章即可从 🔴 升 🟡，并解锁信任评分与集体智能的数据底座。

---

## 附录：本轮审计的验证环境

- 运行时验证：`dev.db` 副本（`audit_tmp.db`，验证后已删除）+ uvicorn 127.0.0.1:8898（验证后已停止）
- 全量测试：`SECRET_KEY/JWT_SECRET_KEY`（≥32 字符）下 `pytest -q`：692 passed / 1 failed / 21m28s
- 期间未修改任何项目源码、未改动 dev.db 原文件
- v1.0 报告中"补 3 列后登录成功"等隔离验证结论，本轮在真实 dev.db 副本上全部得到确认

*本报告基于只读审计与真实运行时验证生成。所有结论均经实际请求/查询复现。*
