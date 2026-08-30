# P2-1 Unified AI Provider — Implementation Report

## Changed files

| File | Change Type | Description |
|------|-------------|-------------|
| `src/providers/llm_base.py` | 新增 | `LLMProvider` 抽象基类，定义 `chat()` / `generate()` / `embeddings()` 接口 |
| `src/providers/self_host.py` | 重写 | 从占位 scaffold 改为真实 Ollama 调用，使用 `ollama.AsyncClient` |
| `src/providers/registry.py` | 增强 | 增加 `has_provider()` 方法，支持 `register` / `get` / `has` 完整操作 |
| `src/providers/mock.py` | 扩展 | `MockRiskAssessmentProvider` 同时实现 `LLMProvider` 接口，兼容两套抽象 |
| `src/providers/openai.py` | 增强 | 完善 `OpenAIProvider` 实现，支持 `chat()` / `generate()` / `embeddings()` |
| `src/providers/__init__.py` | 更新 | 导出所有新 Provider 类和函数 |
| `tests/providers/test_self_host_provider.py` | 新增 | SelfHostProvider 测试：真实调用、超时、不可用、无效模型、构造覆盖 |
| `tests/providers/test_provider_switching.py` | 新增 | Provider 切换测试：mock/openai/self_host 契约、has_provider、默认值、未知 fallback |

**未修改的文件**（保持兼容）：

- `src/ai/providers.py` — 旧 Provider 系统（`BaseProvider`, `ProviderGateway`, `OllamaProvider`）保持原样
- `src/ai/agents.py` — `AgentConfig` / `AgentRuntime` 保持原样
- `src/workforce/employee.py` — `AIEmployeeService.execute_task()` 保持原样，`provider_config` 字段保留
- `src/core/config.py` — Settings 保持原样，`ollama_default_model` 作为合理默认值保留
- `src/api/app.py` — 旧系统启动初始化保持原样
- `src/api/routes/workforce.py` — 旧 Provider 状态路由保持原样

---

## Provider architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     src/providers/ (统一层)                       │
│                                                                   │
│   LLMProvider (ABC)                                              │
│   ├── chat(prompt) → str                                        │
│   ├── generate(prompt) → str                                    │
│   └── embeddings(text) → List[float]                            │
│         │              │              │                          │
│         ▼              ▼              ▼                          │
│   MockRiskAssess  OpenAIProvider  SelfHostProvider               │
│   -mentProvider   (httpx)         (ollama SDK)                   │
│   (mock)          (openai)        (self_host)                    │
│                                                                   │
│   ProviderRegistry:                                              │
│   ├── register_provider(name, cls)                               │
│   ├── get_provider(name) → LLMProvider                           │
│   └── has_provider(name) → bool                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  src/ai/providers.py (旧系统，保留)                │
│                                                                   │
│   BaseProvider → ProviderGateway → AgentRuntime → AI Employee    │
│   ProviderType (7 个 Provider)                                    │
│   保持 P1 已验证的全部行为不变                                     │
└─────────────────────────────────────────────────────────────────┘
```

**两套架构的关系**：

- 新系统 (`src/providers/`) 提供统一 LLM 接口，面向未来 P2-2 ~ P2-5
- 旧系统 (`src/ai/providers.py`) 保持现有 AgentRuntime 向后兼容
- `MockRiskAssessmentProvider` 同时继承 `RiskAssessmentProvider` 和 `LLMProvider`，成为两套系统的桥梁
- 两套系统目前**并存**，不互相依赖，不互相冲突

---

## Unified Provider

**PASS**

`LLMProvider` 抽象基类提供三个核心方法：

```python
class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(self, prompt: str, **kwargs: Any) -> str: ...
    @abstractmethod
    async def generate(self, prompt: str, **kwargs: Any) -> str: ...
    @abstractmethod
    async def embeddings(self, text: str, **kwargs: Any) -> List[float]: ...
```

全部三个实现（Mock、OpenAI、SelfHost）均满足该接口。

---

## Ollama

**PASS**

`SelfHostProvider` 使用 `ollama.AsyncClient` 进行真实调用：

- `chat()` — 调用 `client.chat()`，支持 `temperature` / `max_tokens` 参数
- `generate()` — 调用 `client.generate()`，支持相同参数
- `embeddings()` — 调用 `client.embed()`，检测 501 并返回清晰错误

**错误处理**：

| 场景 | 行为 |
|------|------|
| Ollama 不可达 | `RuntimeError("connection error [provider=self_host, ...]")` |
| 超时 | `RuntimeError("timeout after Xs [provider=self_host, ...]")` |
| 无效模型 | `RuntimeError("API error [provider=self_host, ...]")` |
| 嵌入不支持 | `RuntimeError("not supported [provider=self_host, ...]. Start Ollama with --embeddings flag")` |
| 模型不存在 | `RuntimeError("API error [provider=self_host, ...]")` |

**模型来源**：`model` 参数优先于构造函数传入，其次从 `Settings.ollama_default_model` 读取，不硬编码。

---

## Real local model call

**PASS**

已通过 `test_self_host_chat_returns_real_response` 和 `test_self_host_generate_returns_real_response` 验证：

- 使用本机 Ollama 安装的 `qwen2.5:3b` 模型
- 返回真实 LLM 响应（非 mock 占位符）
- `ollama list` 确认本机已安装：`qwen2.5:3b` (1.9 GB) 和 `qwen2.5:7b` (4.7 GB)

---

## Provider switching

**PASS**

`ProviderRegistry` 支持三种 Provider 切换：

```python
# 切换 Provider
mock = get_provider("mock")       # → MockRiskAssessmentProvider
openai = get_provider("openai")   # → OpenAIProvider
self_host = get_provider("self_host")  # → SelfHostProvider

# 检查 Provider 是否存在
has_provider("mock")              # → True
has_provider("unknown")           # → False

# 别名支持
has_provider("self-host")        # → True
has_provider("selfhost")         # → True

# 默认 / 降级
get_provider()                   # → mock
get_provider("nonexistent")      # → mock (fallback)
```

---

## AI Runtime compatibility

**PASS**

现有 `AgentRuntime` 和 `AIEmployeeService` 完全未修改：

- `AgentRuntime.execute()` 继续通过旧 `ProviderGateway` 调用 Provider
- `AgentConfig` 继续使用硬编码的 `provider` + `model_id`
- `AIEmployee.provider_config` 字段继续存在，保持为 P2-5 可接入状态
- `create_default_agents()` 继续存在，作为 fallback 映射

**全量回归测试通过**：356 passed, 0 failed

---

## P1 regression

**PASS**

P1 已验证的所有功能均未受影响：

- Failure Recovery Chain（16 个测试）
- AI Tool Approval
- Goal Center
- CEO Dashboard
- Workflow Executor
- Task Executor
- 全部单测

---

## Full pytest

```
356 passed, 40 warnings in 201.19s (0:03:21)
```

40 个 warnings 均为 SQLAlchemy 外键排序警告和 asyncio 线程关闭警告，均为已有问题，与 P2-1 修改无关。

---

## Hardcoded model findings

### Category A: 合理的默认配置（保留，不修改）

| 位置 | 值 | 理由 |
|------|------|------|
| `src/core/config.py:68` | `ollama_default_model = "qwen2.5:7b"` | Settings 默认值，用户可通过 `.env` 覆盖 |
| `src/ai/providers.py:971` | `config.metadata.get("model", "qwen2.5:7b")` | 旧系统 fallback，用户可通过环境变量覆盖 |
| `src/api/app.py:183` | `default_model: "qwen2.5:3b"` | 旧系统启动默认值，用户可通过环境变量覆盖 |
| `src/api/routes/workforce.py:860` | `os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")` | 旧系统状态查询 fallback |
| `src/api/provider_catalog.py:46` | `"models": ["qwen2.5:7b", "llama3.1:8b"]` | 静态目录，旧系统行为 |

### Category B: 业务逻辑硬编码（已在 P2-1 范围内处理）

无。新系统 `SelfHostProvider` 的模型名称全部来自配置或构造函数参数，不硬编码。

### Category C: 记录到报告，P2-5 处理

| 位置 | 值 | 理由 |
|------|------|------|
| `src/ai/agents.py:381-468` | 6 个 AgentConfig 的 `provider` + `model_id` | 属于 P2-5 AI Employee Integration 的解耦范围 |
| `src/workforce/employee.py:487-495` | `agent_type` → `AgentConfig` 映射 | 属于 P2-5 的 `provider_config` 接入范围 |

---

## Deferred to P2-5

以下功能在本次 P2-1 中明确不做，留给 P2-5 AI Employee Integration：

1. **AI Employee 使用 `provider_config` 执行任务** — 当前 `execute_task()` 仍通过 `agent_type` → `AgentConfig` 选择模型，`provider_config` 字段保持存在但未接入
2. **AgentConfig 解耦** — 6 个 `AgentConfig` 的硬编码模型保留为 fallback
3. **前端模型选择 UI** — Employee 创建/编辑页面的模型选择
4. **Model Registry 与 Employee 关联** — 统一模型注册与 Employee 配置打通
5. **动态模型发现** — 从 Ollama `/api/tags` 获取模型列表并注册到 ModelRegistry

---

## Out of scope changes

本次 P2-1 明确未修改：

- P2-2 Embedding Pipeline
- P2-3 Knowledge Retrieval
- P2-4 Company Brain
- P2-5 AI Employee Integration
- 旧 Provider 系统 (`src/ai/providers.py`)
- AgentConfig / AgentRuntime
- ProviderGateway
- 数据库模型
- 前端代码
- 已验收的 P1 功能

---

## Blockers

无。

---

## P2-1 ACCEPTED

---

### 关键问题回答

**1. P2-1 是否真正统一 Provider？**

**是**。`LLMProvider` 抽象基类定义了 `chat()` / `generate()` / `embeddings()` 三个方法，Mock、OpenAI、SelfHost 三个 Provider 均实现该接口。`ProviderRegistry` 提供 `get_provider()` / `has_provider()` / `register_provider()` 进行统一管理。

**2. Ollama 是否进行了真实调用？**

**是**。`SelfHostProvider` 使用 `ollama.AsyncClient` 进行真实 Ollama API 调用，已通过测试验证返回真实 LLM 响应。

**3. 是否仍然存在新的模型硬编码？**

**否**。新系统所有 Provider 的模型名称均来自配置或构造函数参数，无硬编码。旧系统（`src/ai/providers.py`、`src/api/app.py`、`src/api/routes/workforce.py`）中的硬编码保留为合理的默认值，属于 Category A。

**4. 现有 AI Runtime 是否保持兼容？**

**是**。`AgentRuntime`、`ProviderGateway`、`AgentConfig`、`create_default_agents()` 均未修改。全量 356 个测试通过。

**5. `AIEmployee.provider_config` 是否被保持为后续 P2-5 可接入状态？**

**是**。`AIEmployee` 模型的 `provider_config` 字段保持原样，`create_employee()` 和 `update_employee()` 方法继续接收该参数。`execute_task()` 暂未使用，等待 P2-5 接入。

**6. 是否误删旧 Provider / AgentConfig / ProviderGateway？**

**否**。旧系统全部保留，两套系统并存。

**7. 全量 pytest 是否通过？**

**是**。`356 passed, 0 failed`。

**8. 是否修改 P2-1 之外的功能？**

**否**。仅修改 `src/providers/` 下的 6 个文件和新增 2 个测试文件，未涉及 P2-2 ~ P2-5 范围。