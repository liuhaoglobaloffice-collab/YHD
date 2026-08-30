# ADR-001: 数据库 Schema 迁移策略（Alembic 双轨制）

## Status

Accepted (2026-08-30)

## Context

dev.db 存在 13 列缺失，导致登录 100% 失败（users 表缺 business_role/data_scope/permissions_config，
auth 查询直接报错）。根因经实测确认：

1. `init_database()` 使用 `Base.metadata.create_all`（src/api/dependencies/database.py:165），
   该机制只建新表，**不会为已有表补列**；
2. 启动时靠一段硬编码的 SQLite 轻量迁移字典补列（src/api/dependencies/database.py:169），
   该字典仅覆盖 5 张表约 10 列，随 ORM 演进已严重过期——dev.db 中 `users.approval_status`、
   `users.ai_budget_monthly` 正是该字典历史补上的，证明此路径确实在启动时执行；
3. `alembic_version` 为空表，alembic/versions/ 仅有 1 个 initial 迁移
   （821f4be8970c_initial_schema.py），版本链从未使用。

## Decision

采用**双轨制**：

- **立即修复轨**：把 13 列全部补入 database.py:169 的迁移字典。列类型与 src/ 对应
  ORM 模型逐一对齐（users 3 列、tasks 2 列、agent_memories 6 列、leads 1 列、
  platform_messages 1 列）。dev.db 下次启动即自动愈合，保留现有数据。
- **长期基线轨**：新增 Alembic 幂等迁移（每列先做存在性检查再 ADD COLUMN），
  对现有库执行 `alembic stamp head` 对齐版本，作为全新环境的建表基线。

**并存纪律**（必须遵守）：
- 新表、新列、索引变更一律走 Alembic 迁移，禁止只改 ORM 不写迁移；
- database.py 的硬编码字典降级为**启动兜底**，仅用于修复历史漂移库，不再作为
  常规演进手段；新迁移落地后应同步清理由字典承担的对应条目，避免双写发散。

## Consequences

**正面**：
- dev.db 立即恢复可用（重启即自愈），登录链路恢复；
- 全新环境获得确定的 schema 基线，不再依赖"先 create_all 再手工补"的隐性顺序；
- 版本链开始工作，后续 schema 变更有审计轨迹。

**负面**：
- 两套机制并存期内存在漂移风险——若开发者绕过 Alembic 直接改 ORM 并依赖字典补列，
  漂移将复现。需以 code review + CI 校验（ORM vs PRAGMA table_info 对比脚本）约束。

## 已知陷阱（写入硬约束）

`alembic_version` 当前为空表且仅有一个 initial 迁移。对已存在全部表的开发库直接执行
`alembic upgrade head` 会因 initial 迁移尝试 CREATE 已存在的表而崩溃。**正确顺序**：
先 `alembic stamp head`（将现有库标记为已到当前版本），此后仅依赖新增的幂等迁移；
或保证所有新迁移对已存在的对象做存在性检查（幂等）。

## Related ADRs

- ADR-003（prod.db 废弃与数据库管理约定）
