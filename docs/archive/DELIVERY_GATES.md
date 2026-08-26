LiuHao AI OS Y1.0 - Delivery Gates

1. 项目交付状态

- 项目：LiuHao AI OS Y1.0
- 当前阶段：Step 2 完成（Supplier 风险评估 → 评估持久化 → Task 创建 → Audit 链路）。
- 当前活动：Step 3 文档收口与交付准备（仅文档与验收门修订）。

2. 自动化测试 Gate (必需)

验收条件：
- 运行命令：pytest -q
- 所有测试必须通过（exit code 0）。

关键测试（必须至少在 Gate 中通过）：
- tests/integration/test_supplier_risk_output_contract.py  — 验证 risk assessment 输出契约是否符合要求。
- tests/integration/test_supplier_risk_task_pipeline.py  — 验证 assessment → task → audit 的完整链路。

说明：CI 环境在运行这些测试时必须提供所需的 secrets（见配置 Gate）。

3. Supplier Risk Contract Gate

验收条件：assess_risk 返回的数据结构（经规范化后）必须包含且类型正确：
- supplier_id (int)
- assessment_id (int 或 null, 但在需要创建 task 的场景下必须为 int)
- risk_level (str)：仅允许取值：LOW, MEDIUM, HIGH, CRITICAL
- risk_score (float)
- overall_score (float)
- risk_factors (dict)
- recommendations (list[str])

备注：risk_level 在系统内部以 UPPERCASE 字符串为契约（便于跨模块映射）。

4. Task Pipeline Gate

验收条件（在生成 Task 的场景下）：
- 风险评估结果已保存到数据库（assessment 保存）
- Task 已由 TaskService.create_task_from_assessment 创建
- Task.metadata 中包含 assessment_reference，至少含 assessment_id 与 supplier_id
- Task.creator_id 在 actor=None 时使用系统占位（zero-UUID），但 Audit 记录中的 user_id 为 None（表示 system-created）
- Audit 日志已创建并能检索到 assessment_reference（用于审计追溯）

5. API Contract Gate

验收条件：
- 任一公开 API（例如 supplier risk endpoints）在返回时满足 Pydantic response 模型：
  - recommendations 返回 List[str]
  - risk_factors 返回 Dict[str, float]（或等效的 JSON 对象）
- 如果路由或文档声明了字段类型，实际返回必须匹配（或进行明确的转换）。

6. 配置 Gate

运行/测试环境必须提供以下配置：
- SECRET_KEY: 应为安全随机字符串，建议长度 >= 32
- JWT_SECRET_KEY: 用于 JWT 签名，建议长度 >= 32
- DATABASE_URL: SQLAlchemy 连接串（例如 sqlite+aiosqlite:///./dev.db 或 PostgreSQL uri）

说明：CI 在执行自动化测试时必须注入这些 secrets，使得 Settings 加载与依赖初始化不会导致失败。

7. 文档 Gate

验收条件：
- README.md 已更新并包含运行步骤、依赖、环境变量说明、以及当前已完成能力的说明。
- DELIVERY_GATES.md（本文件）存在且正确反映 Gate 条件。
- STAGING_CHECKLIST.md 存在并包含上 staging 前的逐项验收步骤（若缺失则需创建）。

8. 禁止项（强制）

- 在未通过上述所有 Gate 前：
  - 不得进入 Step 3 后续开发（例如 Step 3-B 的代码修改或 Step 4）
  - 不得将当前分支合并到下一阶段分支或发布环境

9. 变更治理

- 任何对关键 Gate（测试、契约、配置）相关代码的改动必须伴随：
  - 对应的单元/集成测试更新
  - 更新本 DELIVERY_GATES.md 或 README 中的说明
  - 通过复审并在 CI 中验证

10. 备注与已知问题（审阅员须注意）

- risk_level 在 ORM 中的枚举 value 可能为小写（例如 "low"），但对外契约与 Task 映射使用 UPPERCASE 字符串（LOW/MEDIUM/HIGH/CRITICAL）。实现团队须在接口层统一映射以避免误解。
- routes 中曾引用 RiskLevel.VERY_LOW；当前 models 未定义 VERY_LOW。该项可能导致运行时错误，请在下一次代码修订中修正或将其列入必须修复的 backlog 项。

签署：
- 创建人：Automation / Dev Tools
- 日期：自动生成于仓库修改时（请在 PR 中填写实际变更人）
