变更摘要
- 为 provider metrics 实现“最佳努力”持久化，当环境变量 METRICS_PERSIST=1 时会把采样写入数据库（SQLite / Postgres 等由 DATABASE_URL 控制）。
- 改进持久化鲁棒性：在持久化失败时记录结构化日志并执行单次重试（小退避）。
- 确保后台采样器在应用启动时被唤起：把 lifecycle.startup 的事件发布改为异步发布以触发 subscribe_async 处理器（例如 metrics collector）。
- 添加 CI 友好的集成测试，验证从采样到持久化的端到端流程。

主要改动文件（高层）
- src/api/providers_metrics.py
- src/api/providers_metrics_persist.py
- src/core/lifecycle.py
- tests/integration/test_metrics_persist.py
- scripts/verify_metrics_persist.py

部署 / Staging 操作步骤（建议）
1. 将分支合并到 staging（先在 PR 中审查）。
2. 在 staging 环境中设置 METRICS_PERSIST=1（受控开启）。
3. 配置 DATABASE_URL 指向可写的 staging DB（推荐：Postgres staging 实例或 sqlite 在可写目录下）。
4. 部署服务（rolling restart）。观察日志中是否有“metrics_collector_task_started”，“metrics_persist_error”或“persist_samples_retry_failed”日志条目。
5. 验证：访问 /api/v1/providers/metrics 并查询 provider_metric_samples 表以确认写入。

CI 运行建议
- 把 tests/integration/test_metrics_persist.py 纳入 integration 测试阶段（或单独的 smoke stage）。
- CI runner 需允许写入工作目录（测试会创建临时 sqlite 文件）。
- CI 命令示例： pytest -q tests/integration/test_metrics_persist.py::test_metrics_persist_end_to_end

风险与缓解
- 主动 probe（OpenAI 等）可能会消耗 API 配额或产生费用：在 production 中对云 provider 的探测请谨慎，建议仅在 staging 或在 provider 有明确许可/配额控制时启用。