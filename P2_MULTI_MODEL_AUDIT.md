# P2 Multi-Model / Multi-Provider READ-ONLY AUDIT

## 1. Executive Summary

本项目当前存在**两套并行的 Provider 抽象层**，且 AI Employee 的模型选择完全依赖 `AgentType` → `AgentConfig` 的硬编码映射，导致：

- **AI Employee 与具体模型强耦合**：Employee 通过 `agent_type`（GPT/Claude/Kimi 等）间接选择模型，无法直接指定 Provider + Model
- **模型名称多处硬编码**：`qwen2.5:3b` 和 `qwen2.5:7b` 在至少 5 个位置出现
- **Model Registry 已实现但未被使用**：`ModelRegistry` 类存在但未与 Employee 创建/执行流程关联
- **Ollama 缺乏动态模型发现**：无法利用 Ollama 的 `/api/tags` 接口获取已安装模型列表
- **前端缺失模型管理页面**：`ModelsPage` 只显示 Productization 阶段配置的 Provider，没有模型选择 UI

**核心结论**：当前架构可以支持 Multi-Model / Multi-Provider，但需要做几项关键的解耦改造。

---

## 2. Current Architecture

```
┌─────────────────────────────────────────────────┐
│                  AI Employee                      │
│  ┌───────────────────────────────────────────┐   │
│  │  agent_type: AgentType (GPT/Claude/...)    │   │
│  │  provider_config: {} (未使用)              │   │
│  └──────────────┬────────────────────────────┘   │
│                 │                                  │
│                 ▼                                  │
│  ┌───────────────────────────────────────────┐   │
│  │  AgentRegistry + create_default_agents()   │   │
│  │  → AgentConfig {                           │   │
│  │      provider: ProviderType.OPENAI,       │   │
│  │      model_id: "gpt-4"  ← 硬编码           │   │
│  │    }                                        │   │
│  └──────────────┬────────────────────────────┘   │
│                 │                                  │
│                 ▼                                  │
│  ┌───────────────────────────────────────────┐   │
│  │  AgentRuntime                              │   │
│  │  → 调用 ProviderGateway.complete(          │   │
│  │       provider=config.provider,            │   │
│  │       model_id=config.model_id             │   │
│  │     )                                       │   │
│  └──────────────┬────────────────────────────┘   │
│                 │                                  │
│                 ▼                                  │
│  ┌───────────────────────────────────────────┐   │
│  │  ProviderGateway (src/ai/providers.py)     │   │
│  │  → _get_or_create_provider()               │   │
│  │  → BaseProvider.complete()                  │   │
│  │  → 7 Provider Implementations              │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**两套 Provider 抽象层对比**：

| 维度 | 旧系统 (src/ai/providers.py) | 新系统 (src/providers/) |
|------|------------------------------|------------------------|
| 目标 | 通用 LLM 调用 | 原 Supplier Risk + 统一 LLM 接口 |
| 核心类 | `BaseProvider`, `ProviderGateway` | `LLMProvider`, `ProviderRegistry` |
| Provider 数量 | 7 (OPENAI, ANTHROPIC, GOOGLE, XAI, DEEPSEEK, MOONSHOT, OLLAMA) | 3 (mock, openai, self_host) |
| 被谁使用 | `AgentRuntime` → `AIEmployeeService` | 仅 Supplier Risk |
| 状态 | 活跃使用 | 部分实现 |

---

## 3. AI Employee Model Selection Flow

### 创建 Employee

```python
# src/workforce/employee.py:create_employee()
employee = AIEmployee(
    agent_type=agent_type,           # 例如 AgentType.GPT
    provider_config=provider_config or {},  # 传入但未用于模型选择
)
```

### 执行 Task

```python
# src/workforce/employee.py:execute_task()
# 1. 获取 Employee
employee = await self.registry.get(employee_id)

# 2. 通过 agent_type 找到 AgentConfig
default_agents = create_default_agents()
for agent in default_agents:
    if agent.agent_type == employee.agent_type:
        agent_config = agent  # 包含硬编码的 provider + model_id
        break

# 3. 通过 AgentRuntime 调用 ProviderGateway
response = await runtime.execute(
    agent_type=employee.agent_type,
    messages=messages,
    ...
)
# runtime.execute() 内部调用:
#   gateway.complete(provider=config.provider, model_id=config.model_id, ...)
```

**关键问题**：`AIEmployee.provider_config` 字段在整个执行流程中从未被使用。模型选择完全由 `agent_type` → `AgentConfig` 的硬编码映射决定。

---

## 4. Hardcoded Model Locations

### 4.1 `src/ai/agents.py` - AgentConfig 硬编码

| AgentType | Provider | Model ID | 行号 |
|-----------|----------|----------|------|
| GPT | OPENAI | `gpt-4` | 381 |
| GROK | XAI | `grok-beta` | 399 |
| CLAUDE | ANTHROPIC | `claude-3-5-sonnet-20241022` | 416 |
| DEEPSEEK | DEEPSEEK | `deepseek-chat` | 433 |
| GEMINI | GOOGLE | `gemini-pro` | 450 |
| KIMI | MOONSHOT | `moonshot-v1-8k` | 467 |

### 4.2 `src/ai/providers.py` - OllamaProvider 默认模型

```python
# 行 972
self._ollama_model = config.metadata.get("model", "qwen2.5:7b")
```

### 4.3 `src/core/config.py` - Settings 默认模型

```python
# 行 68
ollama_default_model: str = Field(default="qwen2.5:7b")
```

### 4.4 `src/api/app.py` - 启动初始化

```python
# 行 183
"default_model": "qwen2.5:3b",
```

### 4.5 `src/api/routes/workforce.py` - Provider 状态查询

```python
# 行 860
model = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")
```

### 4.6 `src/api/provider_catalog.py` - Provider 目录

```python
# 行 46
"models": ["qwen2.5:7b", "llama3.1:8b"],
```

---

## 5. Provider Architecture Assessment

### 5.1 现有 Provider 实现

| Provider | 旧系统 (src/ai/providers.py) | 新系统 (src/providers/) | 状态 |
|----------|------------------------------|------------------------|------|
| Mock | `MockProvider` | `MockRiskAssessmentProvider` | 完整 |
| OpenAI | `OpenAIProvider` | `OpenAIProvider` | 完整 |
| Anthropic | `AnthropicProvider` | ❌ | 仅旧系统 |
| Google | `GoogleProvider` | ❌ | 仅旧系统 |
| xAI | `XAIProvider`(GenericHTTPProvider) | ❌ | 仅旧系统 |
| DeepSeek | `DeepSeekProvider`(GenericHTTPProvider) | ❌ | 仅旧系统 |
| Moonshot | `MoonshotProvider`(GenericHTTPProvider) | ❌ | 仅旧系统 |
| Ollama | `OllamaProvider` | `SelfHostProvider` | 双实现 |

### 5.2 抽象接口

**旧系统** (`BaseProvider`):
- `complete(request: ProviderRequest) -> ProviderResponse`
- `health_check() -> ProviderStatus`
- `_execute_with_retry(request) -> ProviderResponse`
- `stream_complete(request)` (部分实现)

**新系统** (`LLMProvider`):
- `chat(prompt: str, **kwargs) -> str`
- `generate(prompt: str, **kwargs) -> str`
- `embeddings(text: str, **kwargs) -> List[float]`

### 5.3 缺口

- 新系统缺少 `list_models()` / `health_check()` 抽象
- 旧系统缺少 `embeddings()` 抽象
- 两个系统之间没有适配层
- 旧系统的 `ProviderGateway` 与新系统的 `ProviderRegistry` 各自独立

---

## 6. Ollama Integration Assessment

### 6.1 当前集成点

| 位置 | 文件 | 说明 |
|------|------|------|
| OllamaProvider | `src/ai/providers.py:963-1100` | 旧系统实现，硬编码模型名 |
| SelfHostProvider | `src/providers/self_host.py` | 新系统实现，使用 Settings 配置 |
| 启动注册 | `src/api/app.py:178-189` | PROVIDER_SETUP 中配置 Ollama |
| 状态检查 | `src/api/routes/workforce.py:858-875` | 调用 `/api/tags` 检查可用性 |
| Provider 目录 | `src/api/provider_catalog.py:44-48` | 静态模型列表 |
| Settings | `src/core/config.py:67-69` | ollama_host / ollama_default_model / ollama_timeout |

### 6.2 动态模型发现

**不存在**。Ollama 的 `/api/tags` 接口仅在 `/provider/status` 端点中被调用检查可用性，但结果未被用于模型发现或注册。

### 6.3 健康检查

- 旧系统 `OllamaProvider` 继承 `BaseProvider.health_check()`，通过发送测试请求检查
- 新系统 `SelfHostProvider` 没有实现 `health_check()`
- 路由层 `/provider/status` 通过 HTTP 调用 Ollama `/api/tags` 检查

### 6.4 模型能力信息

- 旧系统 `OllamaProvider` 没有查询模型能力（context_window, supports_vision 等）
- `ModelConfig` 支持 `supports_*` 字段，但未用于 Ollama
- `SelfHostProvider` 没有实现模型信息查询

---

## 7. Model Registry Assessment

### 7.1 已实现

`ModelRegistry` 类 (`src/ai/providers.py:272-312`)：

```python
class ModelRegistry:
    def register(self, model: ModelConfig)  # 注册模型
    def get(self, provider, model_id) -> ModelConfig  # 查询模型
    def list_models(self, provider, enabled_only) -> List[ModelConfig]  # 列出模型
    def list_by_provider(self, provider) -> List[ModelConfig]  # 按 Provider 列出
```

`ModelConfig` 数据类 (`src/ai/providers.py:50-65`)：

```python
@dataclass
class ModelConfig:
    provider: ProviderType
    model_id: str
    model_name: str
    context_window: int
    supports_streaming: bool = True
    supports_functions: bool = True
    supports_vision: bool = False
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    max_tokens: Optional[int] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 7.2 启动时注册

`src/api/app.py` 在启动时调用 `gateway.register_model()` 注册模型，但仅注册：
1. 环境变量中配置的默认模型（例如 `LLM_PROVIDER=ollama` 时注册 `qwen2.5:3b`）
2. 所有 `create_default_agents()` 中的 agent 模型（`gpt-4`, `grok-beta` 等）

### 7.3 缺口

| 功能 | 状态 |
|------|------|
| Model Metadata | 部分实现 (ModelConfig 支持) |
| Model Capability | 部分实现 (supports_* 字段) |
| Model Status | 未实现 |
| Provider → Model 映射 | 部分实现 (ModelRegistry.list_by_provider) |
| 动态模型发现 | 未实现 |
| 模型生命周期管理 | 未实现 |
| Model ↔ Employee 关联 | 未实现 |

---

## 8. Frontend Models Page Assessment

### 8.1 当前实现

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/ModelsPage.tsx` | 显示 Provider 列表 |
| `frontend/src/services/models.ts` | 调用 `/api/v1/productization/providers` |
| `frontend/src/pages/EmployeesPage.tsx` | 员工管理，无模型选择 |
| `frontend/src/services/employees.ts` | 调用 Employee API |

### 8.2 ModelsPage 显示内容

ModelsPage 从 `/api/v1/productization/providers` 获取数据，该端点返回 Productization 流程中配置的 Provider，数据结构为：

```typescript
interface ProviderInfo {
  provider: string;
  model: string;
  mode: string;
  enabled: boolean;
  registry_key: string;
}
```

### 8.3 缺失功能

| 功能 | 状态 |
|------|------|
| 模型列表展示 | 仅显示 Provider 级别的信息 |
| 模型选择（Employee 创建） | ❌ 无 UI |
| Add Model | ❌ 无 UI |
| Provider 配置 | ❌ 无 UI |
| 动态显示 Ollama 已安装模型 | ❌ 无 UI |
| 模型状态/健康检查 | ❌ 无 UI |
| 模型能力信息 | ❌ 无 UI |

---

## 9. Current Limitations

### 9.1 架构层面

1. **AgentType 与 Model 强耦合**：Employee 的模型选择依赖 `agent_type` 而非直接配置，导致添加新模型需要创建新的 AgentType
2. **两套 Provider 抽象层**：`src/ai/providers.py` 和 `src/providers/` 互不兼容，维护成本高
3. **Model Registry 未被充分利用**：已实现但未与 Employee 创建/执行流程集成
4. **`provider_config` 字段被忽略**：`AIEmployee.provider_config` 存在但从未在执行流程中使用

### 9.2 实现层面

5. **Ollama 无动态模型发现**：无法利用 `/api/tags` 接口获取可用模型
6. **模型名称 5 处硬编码**：`qwen2.5:3b` 和 `qwen2.5:7b` 在多个位置重复定义
7. **AgentConfig 6 处模型硬编码**：6 个 AgentType 各自绑定了具体 Provider 和 Model
8. **前端无模型管理 UI**：无法通过界面添加/配置模型

### 9.3 测试层面

9. **无 Multi-Provider 测试**：现有测试只覆盖 MockProvider 和 OllamaProvider 的基础路径
10. **无 Model Selection 测试**：没有测试 Employee 创建时选择不同模型的情况

---

## 10. Recommended Minimal Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Employee                            │
│  ┌─────────────────────────────────────────────────┐    │
│  │  agent_type: AgentType (可选，向后兼容)          │    │
│  │  provider_config: {                             │    │
│  │    "provider": "ollama",                       │    │
│  │    "model": "qwen3:8b"                         │    │
│  │  }                                              │    │
│  └──────────────┬──────────────────────────────────┘    │
│                 │                                         │
│                 ▼                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Model Selection Policy                          │    │
│  │  1. 优先使用 provider_config 中的配置           │    │
│  │  2. 回退到 agent_type → AgentConfig 映射        │    │
│  │  3. 回退到默认模型                              │    │
│  └──────────────┬──────────────────────────────────┘    │
│                 │                                         │
│                 ▼                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Model Gateway / Provider Layer                  │    │
│  │  → 统一 ProviderGateway (已有)                  │    │
│  │  → 统一 ModelRegistry (已有，需增强)            │    │
│  └──────────────┬──────────────────────────────────┘    │
│                 │                                         │
│        ┌────────┴────────┬───────────────┐               │
│        ▼                  ▼                ▼              │
│  ┌──────────┐    ┌──────────────┐  ┌────────────┐        │
│  │ Ollama   │    │ Provider A   │  │ Provider B │        │
│  │ qwen3:8b │    │ (OpenAI)     │  │ (Anthropic)│        │
│  │ deepseek │    │ gpt-4o       │  │ claude-3   │        │
│  │ gemma    │    │ gpt-4o-mini  │  │ claude-3.5 │        │
│  └──────────┘    └──────────────┘  └────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 核心原则

1. **Employee 不依赖具体模型实现**：通过 `provider_config` 直接指定 Provider + Model
2. **向后兼容**：`agent_type` 的映射作为 fallback 保留
3. **增量改造**：不修改现有架构，只补充解耦层
4. **统一 Model Registry**：作为模型信息的 Single Source of Truth

---

## 11. Required Existing-File Changes

> **注意**：以下为审计识别出的需修改文件清单，不在此阶段执行。

### 需要修改的文件（按优先级排序）

| 优先级 | 文件 | 修改内容 |
|--------|------|----------|
| P0 | `src/workforce/employee.py` | 在 `execute_task()` 中优先使用 `provider_config` 中的 provider/model，回退到 `agent_type` 映射 |
| P0 | `src/ai/agents.py` | 保留 `create_default_agents()` 作为 fallback，标记为 deprecated |
| P1 | `src/ai/providers.py` | 增强 `OllamaProvider` 支持动态模型发现；增加 `list_available_models()` 方法 |
| P1 | `src/providers/self_host.py` | 对齐 `LLMProvider` 接口，增加 `list_models()` 方法 |
| P1 | `src/core/config.py` | 保留 `ollama_default_model` 作为 fallback，不硬编码 |
| P2 | `src/api/app.py` | 启动时从 Ollama 动态获取模型列表并注册到 ModelRegistry |
| P2 | `src/api/routes/workforce.py` | `/provider/status` 返回可用模型列表 |
| P2 | `src/api/routes/productization.py` | `/productization/providers` 返回 ModelRegistry 中的完整模型列表 |
| P2 | `src/api/provider_catalog.py` | 扩展静态目录，或废弃由动态发现替代 |
| P3 | `frontend/src/pages/ModelsPage.tsx` | 增加模型列表展示、模型选择 UI |
| P3 | `frontend/src/pages/EmployeesPage.tsx` | 增加 Employee 创建/编辑时的模型选择 |
| P3 | `frontend/src/services/employees.ts` | 增加 model/provider 字段到 Employee 接口 |

---

## 12. Files That Should NOT Be Changed

以下文件不应在 Multi-Model 改造中修改：

| 文件 | 原因 |
|------|------|
| `src/workflow/*` | Workflow 不关心具体模型 |
| `src/tasks/*` | Task 不关心具体模型 |
| `src/identity/*` | RBAC/Auth 不关心 Provider |
| `src/ai/goal_service.py` | Goal 不关心模型选择 |
| `src/ai/memory_store.py` | Memory 不关心模型选择 |
| `src/ai/cost_tracker.py` | Cost Tracker 只记录，不选择 |
| `src/ai/recovery.py` | Recovery 不关心模型选择 |
| `src/ai/gateway.py` | Gateway 单例不需要修改 |
| `src/knowledge/*` | Knowledge/RAG 不关心模型选择 |
| `src/database/*` | 数据库层不关心 Provider |
| `src/business/*` | 业务层不关心模型选择 |
| `src/crm/*` | CRM 不关心模型选择 |
| `src/integrations/*` | 集成层不关心模型选择 |
| `src/site_os/*` | Site OS 不关心模型选择 |
| `src/dashboard/*` | Dashboard 不关心模型选择 |
| `src/identity/*` | 身份认证不关心模型选择 |

---

## 13. Compatibility / Regression Risks

### 13.1 高风险区域

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 修改 `execute_task()` 的模型选择逻辑 | 所有 Employee 执行路径 | 保留 fallback 到 `agent_type` 映射 |
| 修改 `AgentConfig` 结构 | Agent Runtime 所有调用方 | 只增加字段，不删除现有字段 |
| 修改 `ProviderGateway` 接口 | 所有 Provider 实现 | 增加新方法，不修改现有方法签名 |

### 13.2 无风险区域

- AI Tools
- Tool Approval
- RBAC
- Goal Center
- Planner
- Workflow
- Workflow Executor
- Memory
- Knowledge / RAG
- CEO Dashboard
- Audit Log

### 13.3 兼容性策略

1. 所有修改必须**向后兼容**
2. 现有 `agent_type` → `AgentConfig` 映射作为 fallback 保留
3. 新增字段不影响现有 API 响应格式
4. 测试全部通过后才合并

---

## 14. Test Coverage Gaps

### 14.1 现有测试覆盖

| 测试文件 | 覆盖内容 |
|----------|----------|
| `tests/unit/test_ai_providers.py` | ProviderGateway, MockProvider, OllamaProvider 基础路径 |
| `tests/integration/test_employee.py` | Employee CRUD 和基本执行流程 |
| `tests/integration/test_agent_runtime.py` | AgentRuntime 执行流程 |

### 14.2 缺失测试

| 测试场景 | 原因 |
|----------|------|
| Employee 使用 `provider_config` 执行任务 | 当前 `provider_config` 未被使用 |
| 多个 Provider 动态切换 | 未实现 |
| Ollama 动态模型发现 | 未实现 |
| Employee 创建时选择不同 Provider/Model | 未实现 |
| 模型不可用时 graceful fallback | 未实现 |
| Provider 配置变更后 Employee 执行 | 未实现 |
| 前端模型选择 UI | 未实现 |

---

## 15. Implementation Order

### Phase 1: 解耦 Employee 与 Model（最小改动）

```
1. employee.py: execute_task() 优先使用 provider_config
2. agents.py: 保留 create_default_agents() 作为 fallback
3. 测试：provider_config 执行路径
4. 全量回归测试
```

### Phase 2: 增强 Model Registry

```
5. OllamaProvider: 增加 list_available_models() 动态发现
6. SelfHostProvider: 对齐接口，增加 list_models()
7. 启动时动态注册 Ollama 模型
8. 测试：动态模型发现
9. 全量回归测试
```

### Phase 3: 统一 Provider 抽象层

```
10. 评估是否需要统一 src/ai/providers.py 和 src/providers/
11. 或增加适配层
12. 测试：统一接口
13. 全量回归测试
```

### Phase 4: 前端模型管理

```
14. ModelsPage: 真实模型列表
15. EmployeePage: 模型选择 UI
16. Provider 配置 UI
17. 测试：前端集成
```

---

## 16. Acceptance Criteria

### P0 - 必须通过

- [ ] `provider_config` 中的 provider/model 被 Employee 执行时优先使用
- [ ] 未设置 `provider_config` 时，回退到 `agent_type` 映射正常工作
- [ ] 现有 345+ pytest 全部通过
- [ ] 向后兼容：现有 Employee 无需修改配置即可正常执行

### P1 - 增强

- [ ] Ollama 动态模型发现正常工作
- [ ] 新模型注册到 ModelRegistry 后可在 API 中查询
- [ ] 前端可显示真实模型列表

### P2 - 完善

- [ ] 可通过 UI 为 Employee 选择 Provider + Model
- [ ] 可通过 UI 配置 Provider
- [ ] 新 Provider 可无代码修改加入系统

---

## 关键问题回答

### A. 为什么现在只有 `qwen2.5:3b` / `qwen2.5:7b`？

**根本原因**：模型名称在 5 个位置硬编码，且没有动态模型发现机制。

1. **`src/ai/providers.py:972`** — `OllamaProvider.__init__()` 默认使用 `config.metadata.get("model", "qwen2.5:7b")`
2. **`src/core/config.py:68`** — `ollama_default_model = "qwen2.5:7b"`
3. **`src/api/app.py:183`** — 启动初始化 `"default_model": "qwen2.5:3b"`
4. **`src/api/routes/workforce.py:860`** — 状态查询 `os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:3b")`
5. **`src/api/provider_catalog.py:46`** — 静态目录 `"models": ["qwen2.5:7b", "llama3.1:8b"]`

此外，`AgentConfig` 中的 6 个 AgentType 各自绑定了具体的 Provider 和 Model（GPT→OpenAI/gpt-4, Claude→Anthropic/claude-3-5-sonnet 等），导致 Employee 的模型选择完全被 `agent_type` 锁定。

**Ollama 的 `/api/tags` 接口虽然被 `/provider/status` 路由调用过，但结果仅用于检查可用性，未被用于模型发现或注册。**

### B. 如果未来增加 Qwen3 / DeepSeek / Gemma / Llama / OpenAI / Anthropic，需要修改哪些地方？

**最小修改路径**（仅添加 Ollama 模型）：

| 步骤 | 修改位置 | 修改内容 |
|------|----------|----------|
| 1 | `.env` | 设置 `OLLAMA_DEFAULT_MODEL=qwen3:8b` |
| 2 | 无 | Ollama 侧 pull 模型即可 |

但当前硬编码问题意味着以上修改可能不够。实际需要检查和修改：

**如果通过 Ollama 添加新模型（如 qwen3:8b, deepseek-r1, gemma, llama）**：
- 无需修改代码，只需在 Ollama 中 `pull` 模型，然后修改 `.env` 中的 `OLLAMA_DEFAULT_MODEL`
- 但 Employee 的模型选择仍然受限，因为 `provider_config` 未被使用

**如果通过现有 Provider 类型添加新模型（如 OpenAI 新模型）**：
- 修改 `.env` 中的 `OPENAI_CHAT_MODEL` 等环境变量
- 或修改 `src/api/app.py` 中的 PROVIDER_SETUP 默认值

**如果要添加全新 Provider（如 Anthropic Claude 已存在，但如需添加新 Provider 类型）**：
- 在 `ProviderType` 枚举中添加新类型
- 在 `src/api/app.py` 的 PROVIDER_SETUP 中添加配置
- 在 `ProviderGateway._get_or_create_provider()` 中添加创建逻辑
- 在 `src/api/routes/workforce.py` 的 `/provider/status` 中添加处理分支
- 在 `src/api/provider_catalog.py` 中添加目录项

### C. 如何做到增加模型时不修改 AI Employee 核心代码？

**核心方案：让 Employee 的 `provider_config` 字段真正生效。**

具体改造：

1. **`employee.py:execute_task()`** — 新增模型选择策略：
   ```python
   # 伪代码 - 优先级策略
   if employee.provider_config.get("provider") and employee.provider_config.get("model"):
       # 使用 provider_config 中的配置
       provider = employee.provider_config["provider"]
       model_id = employee.provider_config["model"]
   elif employee.agent_type:
       # 回退到 agent_type → AgentConfig 映射
       agent_config = find_agent_config(employee.agent_type)
       provider = agent_config.provider
       model_id = agent_config.model_id
   else:
       # 回退到默认配置
       provider = "ollama"
       model_id = settings.ollama_default_model
   ```

2. **`AgentRuntime.execute()`** — 接受直接传入的 `provider` 和 `model_id`，不再强制使用 `AgentConfig` 中的值

3. **`provider_config` 存储** — 在 Employee 创建/编辑时通过 API 写入

这样，新增模型时：
- **Ollama 模型**：只需在 Ollama 中 `pull` 模型，然后通过 API/UI 设置 Employee 的 `provider_config={"provider": "ollama", "model": "qwen3:8b"}`
- **OpenAI 模型**：配置 API Key，设置 `provider_config={"provider": "openai", "model": "gpt-4o"}`
- **无需修改 AgentConfig、AgentType 或任何核心代码**

### D. 当前项目距离这个目标还有多远？

**评估：约 60% 已完成。**

| 维度 | 完成度 | 说明 |
|------|--------|------|
| Provider 抽象层 | 70% | `BaseProvider` + `ProviderGateway` 已存在，7 个 Provider 已实现 |
| Model Registry | 60% | `ModelRegistry` 类已实现，但未与 Employee 流程集成 |
| Provider 多样化 | 80% | 7 个 ProviderType 已定义，大部分有实现 |
| 动态模型发现 | 0% | 完全缺失 |
| Employee 模型解耦 | 0% | `provider_config` 字段存在但未被使用 |
| 后端 API | 30% | Provider 状态 API 存在，但模型列表 API 缺失 |
| 前端 UI | 10% | ModelsPage 存在但功能有限，无模型选择 |
| 测试覆盖 | 20% | 基础 Provider 测试存在，Multi-Model 测试缺失 |

**剩余工作量估计**：

| Phase | 工作量 | 涉及文件数 |
|-------|--------|-----------|
| P1: 解耦 Employee 与 Model | 2-3 天 | 2-3 个后端文件 |
| P2: 增强 Model Registry | 1-2 天 | 3-4 个后端文件 |
| P3: 统一 Provider 抽象层 | 2-3 天 | 5-6 个后端文件 |
| P4: 前端模型管理 | 2-3 天 | 3-4 个前端文件 |
| 测试 | 1-2 天 | 2-3 个测试文件 |

**总计约 8-13 天**，但 P1 核心解耦可在 2-3 天内完成，之后即可实现"增加模型不修改 Employee 核心代码"的目标。