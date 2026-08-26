# LiuHao AI OS Y1.0

项目简介
- 项目名：LiuHao AI OS
- 版本：Y1.0
- 当前定位：面向外贸业务的企业级 AI 操作系统原型，优先构建“供应商（Supplier）”业务闭环，整合 AI 风险评估、任务驱动与审计链路。
- 当前完成阶段：Step 2 已完成（Supplier 风险评估 → 评估持久化 → 从评估创建 Task → Audit 日志链路）。当前进入 Step 3 文档收口与交付准备。

环境要求
- Python 版本：3.10 或 3.11（建议使用 3.10+）
- 依赖安装（推荐使用 venv）：
  - python -m venv .venv
  - .\.venv\Scripts\activate  (Windows)
  - pip install --upgrade pip
  - pip install -r requirements.txt
- 运行环境说明：当前代码使用 FastAPI + SQLAlchemy（异步）实现后端，测试使用 pytest。默认测试环境可使用 SQLite（内存）以避免修改实际数据库。

必要环境变量（示例）
- SECRET_KEY: 用于应用加密/配置（请设置为长度 >= 32 的随机字符串）
- JWT_SECRET_KEY: 用于 JWT 签名（请设置为长度 >= 32 的随机字符串）
- DATABASE_URL: SQLAlchemy 连接字符串，例如 sqlite+aiosqlite:///./dev.db 或 PostgreSQL 连接串

测试运行需要的环境说明：
- 在执行 pytest 前，请确保 SECRET_KEY 和 JWT_SECRET_KEY 已在环境变量中设置（可以临时导出或在 CI 中注入），否则部分配置加载会失败。

本地运行方式
1. 安装依赖（见上）
2. 启动服务（开发模式示例）：
   - set SECRET_KEY="$(head -c 32 /dev/urandom | base64)"  (在 Windows PowerShell 中请使用合适的随机生成方法)
   - set JWT_SECRET_KEY="<your_jwt_secret_key>"
   - set DATABASE_URL="sqlite+aiosqlite:///./dev.db"
   - uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
3. 测试命令：
   - pytest -q
   - 关键集成测试（见下）可单独运行以验证 Supplier 风险链路。

当前已完成能力（真实对应代码）
- Supplier Risk Assessment（关键函数与行为）
  - assess_risk: 在 src/business/supplier/risk_agent.py 中实现。流程为：收集供应商数据 → 构建 Prompt → 调用 AI（当前为 mock）→ 解析并规范化输出。
  - assessment 保存: _save_assessment 在 SupplierRiskAgent 中将评估结果持久化为 SupplierRiskAssessment ORM 实例，并调用 save_assessment_knowledge（当前为 Phase 1 的 JSON 存储）。
  - Task 创建: TaskService.create_task_from_assessment（src/tasks/service.py）可基于评估结果创建 Task，且在 Task.metadata 中写入 assessment_reference。
  - Audit 日志: TaskService 在创建 Task 时调用 AuditService.log，记录 action 和 assessment_reference（审计记录可用于追溯）。
- risk_level 规范（统一输出）
  - 已统一为大写字符串：LOW, MEDIUM, HIGH, CRITICAL（agent 层将 risk_level 标准化为 UPPERCASE，以保证跨模块契约稳定性）。

测试验证（关键测试文件）
- tests/integration/test_supplier_risk_output_contract.py
- tests/integration/test_supplier_risk_task_pipeline.py

验证命令：
- pytest -q
（要求在运行前设置 SECRET_KEY 和 JWT_SECRET_KEY 环境变量以避免设置加载错误）

已知限制与行为（必须知悉）
1. AI 异常返回处理
   - AI Provider 集成当前为 MOCK（src/business/supplier/risk_agent.py 中 _call_ai_analysis 返回模拟 JSON）。
   - 当 AI 返回空、非 JSON 或缺少字段时，Agent 有兜底逻辑：返回默认评估（_get_default_assessment），并记录 error 日志。文档中后续会记录这些失败模式与处理方式。
2. assessment_id 要求
   - create_task_from_assessment 要求 assessment payload 中必须包含 assessment_id（否则抛出 ValueError）。这是 Task 创建契约，调用方必须保证评估已持久化并具有 assessment_id。
3. system actor 行为（actor=None 的含义）
   - 若在 create_task_from_assessment 中传入 actor=None，则 Task.creator_id 会被设置为占位 zero-UUID 字符串（"00000000-0000-0000-0000-000000000000"）以满足数据库约束；但 Audit 记录的 user_id 会为 None，表示系统自动创建。该行为已在代码中实现并应在审计查询中注意区分 system-created 与真实用户创建的记录。

附：代码相关注意事项（开发者读）
- risk_level 大写／小写差异：ORM models 中 RiskLevel.value 为小写（"low" 等），但 agent 与 routes 在返回 API 时使用大写字符串（"LOW" 等）。请在对接二次开发时注意字段大小写映射，或在接口层统一转换。
- routes 中 risk distribution 的实现使用了 RiskLevel.VERY_LOW 的取值位置，当前 models 未定义 VERY_LOW；该处已在代码层面做了部分容错（agent.get_risk_distribution 确保返回 UPPERCASE keys），但建议在后续迭代中统一枚举或修复 routes 中的直接引用。

如何继续
- 当前 Step 2 的实现已通过集成测试（本地验证）。下一步（经你批准）会是把 README 的内容加入仓库（已在本次操作中完成），并随后创建 DELIVERY_GATES.md 与 STAGING_CHECKLIST.md（需你另行批准）。

联系方式
- 如需我继续进行 Step 3-B.2（创建 DELIVERY_GATES.md），请回复批准。
