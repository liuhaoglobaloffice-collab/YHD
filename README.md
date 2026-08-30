# 鎏灏 LiuHao AI OS Y1.0

面向外贸企业的 **AI 操作系统**：老板设定目标（Goal），系统自动规划（Planner）、编排工作流
（Workflow）、调度 AI 员工（AI Employee）调用真实大模型与工具执行任务，全过程落库、留痕、
可审计、可度量。

- 版本：Y1.0（可运行 → 可操作 → 可验证 → 可部署 → 可真实使用）
- 技术栈：FastAPI + SQLAlchemy(async) + PostgreSQL/SQLite + React + TypeScript + Tailwind + Docker
- 知识地图：见 [CODE_WIKI.md](./CODE_WIKI.md)

---

## 一、最快启动（Docker，推荐）

前置：Docker + Docker Compose。

```bash
# 1. 准备环境变量（密钥绝不入库；.env 已被 .gitignore 排除）
cp .env.example .env
#   编辑 .env，至少设置：
#   SECRET_KEY=<≥32 位随机字符串>
#   JWT_SECRET_KEY=<≥32 位随机字符串>
#   POSTGRES_PASSWORD=<强密码>
#   可选：OLLAMA_ENABLED=true + OLLAMA_HOST（本地大模型）、OPENAI_API_KEY 等

# 2. 一键起全栈（backend + frontend + postgres）
docker compose up -d --build

# 3. 等待健康检查通过
docker compose ps   # backend / database 应为 healthy
curl http://localhost:8000/api/v1/health/ready
```

访问：

| 入口 | 地址 |
|---|---|
| 前端产品界面 | http://localhost |
| 后端 API | http://localhost:8000/api/v1 |
| 交互式 API 文档 | http://localhost:8000/docs |
| Prometheus 指标 | http://localhost:8000/metrics |

## 二、第一次真实使用

1. 浏览器打开 http://localhost ，首次进入为**注册老板账号（OWNER）**页：填写用户名 / 邮箱 /
   密码，注册后该账号自动成为企业主账号，拥有全部权限。
2. 登录后进入 **Dashboard**：查看 AI 员工在岗数、进行中/已完成/异常任务、目标进度、
   系统健康度与实时活动流（全部来自真实数据库状态）。
3. 到 **Models / Provider** 页配置 AI 提供商：
   - 本地：安装 [Ollama](https://ollama.com) 并 `ollama pull qwen2.5:3b`（对话）与
     `ollama pull nomic-embed-text`（向量），在 `.env` 设 `OLLAMA_ENABLED=true`、
     `EMBEDDING_PROVIDER=ollama`；
   - 或云端：设置 `LLM_PROVIDER=openai` + `OPENAI_API_KEY`。
4. 到 **AI 员工**页查看/添加员工；到 **知识库**页上传文档（自动 解析→分块→向量化→入库），
   并可在语义检索框验证 RAG。
5. 到 **目标中心**创建目标（如“开发美国市场获取潜在客户”），系统经 Planner 生成 Workflow，
   Executor 调度 AI 员工执行；结果、Memory、Audit、Metrics 全部自动落库，目标最终进入
   `completed` 或 `failed/recovered`。

## 三、部署后冒烟验证

```bash
python scripts/verify_api_smoke.py \
  --username <老板账号> --password <密码> [--base http://localhost:8000]
```

覆盖前端全部核心页面依赖的 28 个 API（Auth/Dashboard/员工/目标/工作流/任务/知识库语义检索/
审计/审批/Provider/CRM/子账号/业务指标/健康/成本/角色/权限/报价/平台账户 + Prometheus）。
退出码 0 即全通。

## 四、开发模式（本地热重载）

```bash
python -m venv .venv
.\.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env            # 填写密钥（dev 默认 SQLite ./dev.db）

bash scripts/start_api.sh       # 后端 http://localhost:8000

cd frontend
npm install
npm run dev                     # 前端 http://localhost:3000
```

> `SECRET_KEY` 与 `JWT_SECRET_KEY` 必须各自 ≥32 字符，否则配置校验直接失败；
> `scripts/start_api.sh` 在未设置时提供合规的开发默认值。

## 五、测试

```bash
# 后端全量回归（SQLite 临时库，无需外部服务）
pytest -q

# 前端构建 + 前端单测
cd frontend && npm run build
```

## 六、Y1.0 核心能力（真实代码对应）

- **真实持久化**：API → Service → Repository → Database 全链路；核心实体（Users / Companies /
  AI Employees / Goals / Workflows / Executions / Knowledge / Documents / Chunks / Embeddings /
  Memories / KPI / Budget / Audit / Metrics）均落 PostgreSQL（生产）或 SQLite（开发/测试），
  启动时自动做增量列迁移与孤儿执行恢复。
- **安全收口**：JWT 认证 + RBAC（OWNER/ADMIN/USER/VIEWER + 外贸业务角色）+ 数据可见性隔离
  （主/子账号、DataScope）+ 审批 + 审计日志 + 密钥环境注入；OWNER 被降权为 viewer 后权限一致收
  紧；所有路由权限码经静态审计测试守护（`tests/security/test_rbac_unified.py`）。
- **AI Provider**：Provider Registry 统一接入 Ollama（本地）/ OpenAI 兼容端点，含降级重映射；
  Chat / Generate / Embedding 真实调用；Mock 仅存在于单元测试。
- **Knowledge / RAG**：文档上传 → 解析 → 分块 → Embedding（nomic-embed-text 真实向量）→
  存储 → 语义检索（向量 + 全文，自动排除归档/删除文档）→ 注入上下文；Memory 写入/读取/检索
  按用户隔离。
- **Goal / Workflow 闭环**：Goal → Planner → Workflow → Executor → AI Employee → Provider →
  LLM/Tool → Execution → Result → Memory → Audit → Metrics → Goal Completion；失败链路含
  Detection → Recovery → Retry/Alternative。
- **前端产品化**：Dashboard（实时活动 + 系统健康 + 告警）、AI 员工、目标中心、工作流、任务、
  知识库（上传/语义检索/记忆）、CRM、多平台、报价、独立站/SEO、安全（子账号/角色/权限/审批）、
  模型/Provider、指标等页面全部接真实 API，空态/加载/错误态完备。
- **可观测**：`/metrics`（Prometheus 文本指标）、AI 成本汇总、审计日志、系统健康端点。

## 七、目录速览

```
src/
  api/            FastAPI 路由、应用装配、依赖注入
  identity/       认证、RBAC/ABAC、主子账号、审计
  business/       业务域服务（供应商、任务、报价、业务指标）
  workforce/      AI 员工注册、生命周期、绩效
  ai/             Provider、Agent、Planner、Recovery、Trust
  knowledge/      文档、分块、检索、记忆
  workflow/       工作流定义与执行器
  scheduler/      老板离线自主经营调度器（可选开启）
frontend/src/     React 页面、组件、API services
scripts/          启动、种子、校验、部署后冒烟脚本
tests/            pytest 全量回归（单元/集成/API/安全/SRE）
docker-compose.yml  backend + frontend + postgres 生产编排
```
