# Core Business Flow Assessment — LiuHao AI OS Y1.0

Date: 2026-08-25T15:03:30-07:00

Purpose

评估 LiuHao AI OS Y1.0 在进入“核心业务能力建设”阶段前的主业务链路和能力准备度。基于当前代码、测试及文档（Step 1/2 已完成、Step 3 文档收口），对企业基础链路、Supplier Risk 主链、AI Agent 主链以及企业操作系统能力进行逐项评估并提出先决补充与优先级建议。

Summary Recommendation

整体结论：基础能力已具备进入核心业务能力建设的条件，但存在若干需要在 Step 4 前列为 P0/P1 处理的项（非全部致命）。建议在进入大规模核心开发前，优先处理 /ready、enum 一致性、VERY_LOW 引用、以及 .gitignore 清理与 production-grade AI provider 设计。

评分（主链完整度）
- 企业基础链路总体完整度：B-（基础模型存在，多个实体实现或占位，需补充）
- Supplier Risk 主链完整度：A-（核心闭环已实现并通过集成测试）
- AI Agent 主链完整度：C+（Agent 核心能力已实现雏形，LLM 调用为 mock，缺少 RAG/长期 memory）
- 企业操作系统能力（Task/Workflow/Knowledge/Permission）：B-（Task、Audit 有实现；Workflow、Knowledge、Memory、Permission 为部分或占位）

详尽评估

1) 企业基础链路（Supplier / Customer / Product / Opportunity / Business data）

发现与分析：
- Supplier：明确实现且被测试覆盖（supplier 创建、查询、风险评估触发、risk-history），在 src/business/supplier/ 与 routes 中有具体实现。
- Customer：在当前变更集与测试中未见完整的 Customer CRUD 与业务链路证据（仓库存在 src/identity 或其他模块，可能包含用户/组织模型，但未见完整 CRM 流程测试）。
- Product / Opportunity：同样未在本次交付的测试或文档中找到完整实现或关键集成测试。可能存在占位模型或即将迭代的 scaffold（需在代码中进一步确认）。
- Business data（交易/机会/订单等）：未见完整流程或 tests 覆盖。仓库包含大量模块与例子，但核心外贸/CRM 表与流程尚不足以直接构建上层功能。

结论：Supplier 是首要并已稳定的领域；Customer/Product/Opportunity 目前处于部分实现或缺失状态。若要构建完整 CRM/供应链/外贸模块，需要先补齐 Customer、Product、Opportunity 的数据模型和 CRUD/关联测试。

必须补充项（进入核心业务建设前）
- 建立并验证 Customer、Product、Opportunity 的数据模型与 API（P0）
- 增加跨实体的关联测试（例如 Supplier ↔ Product ↔ Opportunity 的端到端示例）（P1）

2) Supplier Risk 主链（详细节点）

流程：
Supplier → Risk Assessment → Risk Score → Risk Level → Task Creation → Workflow → Audit Log → Metrics

节点逐项检测：
- Supplier：已存在且可创建（API + tests）。
- Risk Assessment：实现（src/business/supplier/risk_agent.py），含 prompt 构建、AI 调用（当前为 mock 实现）、解析与规范化。
- Risk Score / Risk Level：agent 层计算并规范化为 UPPERCASE（LOW/MEDIUM/HIGH/CRITICAL），risk_score/overall_score 为 float。
- Assessment Persistence：已将评估持久化为 ORM 实体并返回 assessment_id（被集成测试验证）。
- Task Creation：create_task_from_assessment 已实现，包含 priority 映射与 metadata.assessment_reference 写入（被测试覆盖）。
- Workflow：存在 src/workflow/ 模块目录；但工作流引擎功能（复杂的状态机、自动推进、子任务展开等）程度不确定，当前 pipeline 依赖 TaskService 触发与 Audit。对接复杂 workflow 需进一步增强（P1）。
- Audit Log：当 Task 创建时写入 Audit（实现并由 tests 验证），包含 assessment_reference。
- Metrics：项目包含 metrics persistence 的测试与可选 router；在运行时可选启用（已测试或 N/A）。

追踪性与可扩展性：
- 每个关键节点都可追溯（assessment_id、task.metadata.assessment_reference、audit 记录），端到端链路在测试中通过验证。
- 扩展性良好：TaskService 与 Agent 层分离，metadata 可拓展，Audit 模型支持追溯。

结论：Supplier Risk 主链是仓库的成熟能力，可作为核心业务能力建设的主线。

3) AI Agent 主链（Input → AI Analysis → Decision → Task → Execution → Feedback → Learning）

当前实现程度：
- Input：供应商属性和历史可作为输入（实现了获取并组装 prompt 的逻辑）。
- AI Analysis：有 AI 调用封装与解析，但当前 LLM Provider 为 mock 模拟，生产接入未实现。
- Decision：Agent 将输出规范化、映射 risk_level 与 scores，并返回结构化结果；默认兜底处理 AI 异常（empty/invalid JSON），良性设计。
- Task：Decision 可触发 TaskService.create_task_from_assessment；映射优先级并写 metadata，任务生成链路存在。
- Execution：任务执行和 workflow 执行器不完整或为基础实现（没有复杂自动执行系统），主要依赖任务存储与人工/外部流程执行。
- Feedback：没有完整的自动反馈/label 收集闭环；可以通过 Audit/Task status 做人工反馈，但自动化学习流水线（将执行结果喂回 Agent 并更新模型/knowledge）未实现。
- Learning：RAG/知识库/长期 memory 未完整；有 save_assessment_knowledge stub/实现但非成熟 RAG。

结论：AI Agent 主链具备“决策→触发任务”的关键环节，但在执行自动化、反馈收集与持续学习方面仍需大量建设。短期可用人工闭环与半自动化流程支撑业务。

4) 企业操作系统能力评估（Task/Workflow/Knowledge/Memory/Permission）

发现：
- AI Employee：Agent 与 Task 的组合可模拟 AI Employee 的部分能力（评估并创建任务），但没有完整的 AI 员工管理、分配、长期记忆或跨会话 agent 协作体系。
- Task System：已实现 Task 创建、metadata、优先级映射及 Audit；Task 存储与查询能力存在，且可扩展（Service 层设计良好）。
- Workflow：有 workflow 目录与初步组件，但缺乏完整流程引擎支持（例如基于状态机的自动推进、事件驱动工作流引擎）。
- Knowledge：存在 assessment 知识的保存接口，但未见成熟的知识索引/RAG 层与检索管道。
- Memory：未见长期记忆存储与检索的成熟实现（例如对历史评估/行动的 embedding 索引与检索）。
- Permission：有 src/identity 或相关模块，但细粒度权限与多租户隔离证据有限；审计记录存在，可用于合规性追溯。

结论：Task 与 Audit 已具备企业操作系统的基础能力；Workflow、Knowledge、Memory、Permission 为部分或需求实现（需要在 Step 4 中优先建设以支持大规模企业能力）。

5) 输出：主链完整度评分与待办

主链完整度评分（0-100）：
- Supplier Risk 主链：90/100
- AI Agent 主链：60/100
- 企业基础链路（全域 CRM/产品/机会）：55/100
- 操作系统能力（综合 Task/Audit/Workflow/Knowledge）：65/100

进入核心业务建设前必须补充项（P0/P1/P2）
- P0（必须在进入 Step 4 前确认/处理）
  - Owner 确认 /api/v1/ready 的接受策略或实现 /ready（部署自动化可能依赖）。
  - 修复 routes 中 RiskLevel.VERY_LOW 的引用或在 models 中补充 enum（防止运行时异常）。
  - 在 repo 中清理/更新 .gitignore，避免将 dev.db、frontend/dist、node_modules 等提交到 PR 中（影响 CI/PR 整洁）。

- P1（Step 4 初期优先处理）
  - 统一 risk_level 枚举表述（ORM 与 API 一致化）。
  - 设计并开始实现生产级 LLM Provider 接入（可插拔策略：mock→provider adapters）。
  - 增补 Customer/Product/Opportunity 数据模型与 CRUD API，及相关集成测试。
  - 增强 Workflow 引擎能力（或集成现成工作流引擎）以支撑自动化执行场景。

- P2（优化/长期）
  - 构建知识索引 / RAG 层与长期 Memory（embedding store、retrieval layer）。
  - 增加自动化反馈链路：任务执行结果回流至 Agent 学习管道。
  - 改善测试覆盖率与降低现有 pytest warnings。

6) 非阻塞优化项
- 改善文档（已完成大部分）— 对生产部署的 uvicorn factory 用法、token 获取、健康检查端点做更细化说明。
- 引入 metrics dashboard 与 alerting（如果业务需要）。

Appendix: 证据引用
- tests/integration/test_supplier_risk_output_contract.py
- tests/integration/test_supplier_risk_task_pipeline.py
- src/business/supplier/risk_agent.py
- src/tasks/service.py
- src/api/routes/supplier_risk.py
- STAGING_ACCEPTANCE_REPORT.md

---

Prepared by: Copilot CLI runtime in VS Code (automation analysis).