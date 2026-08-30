# ADR-003: prod.db 废弃与数据库管理约定

## Status

Accepted (2026-08-30)

## Context

项目根目录散落 4 个 SQLite 库，无任何管理约定：dev.db、prod.db、test.db、verify_e2e.db
（2026-08-30 实测）。其中：

- **prod.db 仅 51 张表，且同样缺 users 表 3 列**（business_role/data_scope/
  permissions_config），登录功能在该库上同样不可用；
- 库内**无真实生产数据**——项目从未真正部署上线，"prod" 只是名字；
- 真正承载开发与验证的是 dev.db（最近修改时间也最新）。

保留一个不可用且无数据的"prod.db"只会制造误用风险：任何人把它当生产库配置启动，
得到的是一个登录都失败的系统。

## Decision

1. **prod.db 废弃归档**：重命名为 `prod.db.archived-20260830` 留档（不删除），
   在修复报告中注明。
2. **确立数据库管理约定**：
   - `dev.db` 为**唯一开发库**——所有开发/联调数据落此，schema 演进按 ADR-001
     双轨制执行；
   - 测试库由 pytest fixtures 自建（test.db），测试结束自清理，不入版本库、
     不手工维护；
   - 验证库（verify_e2e.db）仅用于端到端验收，**用后即清**，不留作环境。
3. **部署边界写明**：SQLite 仅限开发与测试。真实生产部署时按 docker-compose
   既定方案走 PostgreSQL，届时 schema 以 Alembic 迁移基线（ADR-001 长期轨）为准
   在空库上 `upgrade head` 建表，**不迁移 SQLite 数据文件**。

## Consequences

**正面**：
- 消除"误用 prod.db 导致系统不可用"的整类风险；
- 数据库职责单一化：开发一个库、测试自建、验证即用即清，排查问题时无歧义；
- 迁移基线在 PostgreSQL 上可直接重建，为未来部署扫清 schema 障碍。

**负面**：
- 归档文件留在根目录（约 1.2MB），需在约定中标注其"已废弃、勿用"性质；
- PostgreSQL 部署路径目前无实测验证（Alembic 迁移的幂等逻辑需兼容 PG 方言），
  属部署阶段工作，本轮不做。

## Related ADRs

- ADR-001（Alembic 双轨制——迁移基线是 PG 部署的前提）
- ADR-002（员工编制数据落 dev.db）
