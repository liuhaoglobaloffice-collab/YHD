# ADR-002: AI 员工 Provider 绑定策略（provider_config 员工级覆盖）

## Status

Accepted (2026-08-30)

## Context

10 名 AI 员工的 agent_type 经静态映射绑定了境外 Provider（OpenAI/Anthropic/Google 等），
而系统中 6 个境外 API Key 全部为空；唯一注册可用的 Provider 是本地 Ollama
（qwen2.5:3b）。结果是 0 名员工可实际执行任务——目标激活/执行全链路被
"Provider not registered" 阻断。

绑定关系的结构性缺陷：agent_type → 默认 AgentConfig（含 ProviderType）是**静态映射**
（src/workforce/employee.py:494-506），员工的 Provider 完全由其岗位类型决定，
运行环境（哪些 Provider 可用）变化时无法在员工层面调整。

service 层实际已具备解耦能力：`src/workforce/employee.py:508-533` 实现了
provider_config 覆盖逻辑——employee.provider_config 中的 provider/model 字符串
经 `ProviderType(provider_str)` try/except 校验后，用 `dataclasses.replace`
生成覆盖版 AgentConfig。但 API 层的 PATCH 路由不透传该字段，配置无法从外部更新。

## Decision

1. **provider_config 升级为员工级 Provider/模型覆盖的一等配置**：
   `UpdateEmployeeRequest` 增加
   `provider_config: Optional[Dict[str, Any]] = None` 并透传至 service 层，
   使 PATCH /api/v1/workforce/employees/{id} 可更新并落库该配置。
2. **全员默认绑定本地 Ollama**：按 5 部门编制
   （AgentRouter 的 AGENT_MAPPING，src/ai/agent_router.py:33-54：
   research/marketing/sales/business/ceo_assistant 五类映射）
   重绑/新建员工，全员
   `provider_config = {"provider": "ollama", "model": "qwen2.5:3b"}`，status=active。
3. 编制数据用脚本/SQL 落入 ai_employees 表（config 列存 JSON），并固化到
   seed 脚本保证可重建。AgentRouter 的 5 部门映射决定编制下限：每部门至少
   一名在岗员工，否则任务路由时报 "No ... AI employee available"。

## Consequences

**正面**：
- Provider 与员工岗位解耦：环境变化（换 Key、换本机模型）时 PATCH 即可热切换，
  无需动 agent_type 或代码；
- 10 名员工立即可执行，目标激活/执行链路（AC-03/AC-04）打通；
- Provider 合法性校验复用现有 try/except（employee.py:519-522），
  非法 provider 字符串仅告警并回退默认值，不致 500。

**负面**：
- provider_config 覆盖与 agent_type 语义可能不一致（如 research 岗绑到无研究能力的
  模型），系统不做能力校验，仅靠人工配置正确性。缓解：provider 字符串合法性已校验，
  模型能力匹配由编制文档约束；
- 覆盖配置为自由 Dict，schema 无强约束，后续需在 API 层收紧字段白名单。

## Related ADRs

- ADR-003（数据库管理约定：编制落 dev.db）
