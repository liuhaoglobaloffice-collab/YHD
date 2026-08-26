LiuHao AI OS Y1.0 - Staging 验收清单

1. Staging 验收目标

- 项目：LiuHao AI OS Y1.0
- 目的：验证 Step 2 已完成的 Supplier 风险评估与风险→Task 闭环在 Staging 环境中可用、可追溯并满足最基本的生产就绪要求。

2. 环境准备检查

- Python 版本：3.10 或 3.11
- 依赖安装：pip install -r requirements.txt
- 必要环境变量（已设置并可在进程内读取）：
  - SECRET_KEY (建议长度 >= 32)
  - JWT_SECRET_KEY (建议长度 >= 32)
  - DATABASE_URL (例如 sqlite+aiosqlite:///./staging.db 或 PostgreSQL URI)

- 在 Windows PowerShell 下设置示例（临时，仅在当前 shell 有效）：
  - $env:SECRET_KEY = "<your-secret-32-or-more>"
  - $env:JWT_SECRET_KEY = "<your-jwt-secret-32-or-more>"
  - $env:DATABASE_URL = "sqlite+aiosqlite:///./staging.db"

3. 服务启动检查

- 启动服务（示例）：
  - uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
- 确认服务正常运行（示例验证命令）：
  - curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
  - curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ready
  - 在 Windows PowerShell 中： (Invoke-WebRequest http://localhost:8000/health).StatusCode

- 说明：如果项目未实现 /health 或 /ready，请使用根路径或其他现有健康检查端点替代。

4. Supplier Risk 流程验收

- 执行：触发风险评估
  - POST /suppliers/{supplier_id}/assess-risk
  - 示例（curl）：
    - curl -X POST "http://localhost:8000/suppliers/1/assess-risk" -H "Content-Type: application/json" -d '{}' 
- 验证 assess_risk 返回结构（并与 API 的历史记录比对）：
  - 必检字段：supplier_id, assessment_id, risk_level, risk_score, overall_score, risk_factors, recommendations
  - risk_level 允许值（必须为大写字符串）：LOW, MEDIUM, HIGH, CRITICAL
- 验证步骤示例：
  1. POST /suppliers/{id}/assess-risk，记录 response 中的 assessment_id
  2. GET /suppliers/{id}/risk-history?limit=1，确认最新记录的 id 与步骤 1 的 assessment_id 一致
  3. 确认 response 中 recommendations 为数组，risk_factors 为对象

5. Risk → Task 链路验收

- 验证方法（建议）：
  - 使用 tests/integration/test_supplier_risk_task_pipeline.py 运行自动化验证（推荐）
  - 或手动验证流程：
    1. 触发评估（见第 4 步），获得 assessment_id
    2. 执行或触发 create_task_from_assessment（通常由系统在评估后触发，或在测试中模拟），
       - 如果系统自动创建 Task，请等待短时间后查询 Tasks
    3. 查询任务：如果存在 Task 查询 API，请使用 /tasks 或管理控制台查询；否则，通过数据库查看 tasks 表（仅在有权限时）
    4. 验证 Task.metadata 中包含 assessment_reference（包含 assessment_id 与 supplier_id）
    5. 验证 Audit 日志已产生并可检索到 assessment_reference（可通过 Audit 查询 API 或数据库 audit 表）

- 说明：如无 Task 查询 API，请使用集成测试验证（tests/integration/test_supplier_risk_task_pipeline.py）或由运维查询数据库。

6. API 返回检查

- recommendations 字段应为 List[str]
- risk_factors 字段应为 Dict[str, float] 或可 JSON 序列化的对象
- API 响应应与 Pydantic 模型匹配（避免类型不一致导致消费者异常）
- 发生不匹配时：记录示例请求/响应并作为缺陷提交到 backlog

7. Metrics 检查（如果启用）

- 若项目启用了 metrics persistence：
  - 验证 metrics 已写入持久化层（根据项目实现检查相应表或存储）
  - 示例：检查 metrics 表行数或通过 metrics 查询 API

8. 测试验收

- 推荐顺序执行以下命令（在 staging 环境或等效配置下）：
  - pytest tests/integration/test_supplier_risk_output_contract.py -q  (验证 assess_risk 输出契约)
  - pytest tests/integration/test_supplier_risk_task_pipeline.py -q  (验证 assessment→task→audit 链路)
  - pytest -q (全量测试)
- 要求：所有测试通过（exit code 0）

9. Staging 通过标准

- 满足上述所有检查与测试通过，即视为 Staging 验收通过。
- 仅在所有项通过后，方可进入后续开发阶段或将代码 promoted 到下一阶段。

10. 禁止事项

- 未通过 checklist 上任一项，不得进入 Step 4。
- 未通过 checklist 上任一项，不得扩展新的业务模块或上线新功能到 Staging/Production。

11. 验证记录

- 建议在执行验收时记录每一项的检查结果（通过/不通过/备注），并将记录附在变更记录或发布说明中以便审计。记录应包含：
  - 请求示例（curl 或 API 调用）
  - 关键响应摘要（包含 assessment_id、task_id、audit_id 等）
  - 证据链接（日志、数据库查询结果或测试输出）

签署：
- 验收人：
- 日期：
