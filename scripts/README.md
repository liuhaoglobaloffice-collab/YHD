# 📁 Scripts 目录说明

本目录包含项目的所有辅助脚本和工具，已按功能分类归档。

---

## 📂 目录结构

```
scripts/
├── admin/          管理脚本 (7 个)
├── backups/        备份文件 (13 个)
├── checks/         检查脚本 (5 个)
├── fixes/          修复脚本 (14 个)
├── migrations/     迁移脚本 (7 个)
├── tests/          测试脚本 (5 个)
└── updates/        更新脚本 (1 个)
```

---

## 🔧 各目录说明

### 1. admin/ (管理脚本)
用于系统管理和初始化的脚本。

**文件列表**:
- `init_database.py` - 初始化数据库
- `create_admin.py` - 创建管理员用户
- `create_admin_prod.py` - 生产环境管理员创建
- `recreate_admin.py` - 重建管理员
- `list_users.py` - 列出所有用户
- `generate_token.py` - 生成访问令牌
- `apply_test_fixes.py` - 应用测试修复

**使用示例**:
```bash
cd D:\LiuHao-AI-OS
python scripts/admin/init_database.py
python scripts/admin/create_admin.py
```

---

### 2. backups/ (备份文件)
历史代码版本的备份文件，仅供参考。

**文件类型**:
- `*.backup` - 旧版本备份
- `*.backup2` - 次级备份
- `*.bak` - 临时备份

**注意**: 这些文件不应用于生产环境，仅作历史记录保留。

---

### 3. checks/ (检查脚本)
用于验证系统状态和配置的脚本。

**常用脚本**:
- `check_*.py` - 各类系统检查

**使用示例**:
```bash
python scripts/checks/check_database.py
```

---

### 4. fixes/ (修复脚本)
用于修复特定问题的临时脚本。

**文件数量**: 14 个

**命名规范**: `fix_<问题描述>.py`

**使用场景**:
- 数据修复
- 配置修复
- 结构调整

---

### 5. migrations/ (迁移脚本)
数据库迁移和数据结构变更脚本。

**文件列表**:
- `migrate_*.py` - 数据迁移
- `complete_*.py` - 迁移完成脚本

**执行顺序**: 按文件名时间戳顺序执行

---

### 6. tests/ (测试脚本)
独立测试脚本，补充 tests/ 目录的单元测试。

**用途**:
- 快速功能验证
- 集成测试
- 性能测试

---

### 7. updates/ (更新脚本)
系统更新和升级脚本。

**文件列表**:
- `update_knowledge_api.py` - 知识库 API 更新

---

## 🚀 快速使用指南

### 初次部署
```bash
# 1. 初始化数据库
python scripts/admin/init_database.py

# 2. 创建管理员
python scripts/admin/create_admin_prod.py

# 3. 检查系统状态
python scripts/checks/check_database.py
```

### 日常维护
```bash
# 列出用户
python scripts/admin/list_users.py

# 生成访问令牌
python scripts/admin/generate_token.py

# 执行修复（按需）
python scripts/fixes/<specific_fix>.py
```

### 数据迁移
```bash
# 按顺序执行迁移脚本
python scripts/migrations/migrate_001.py
python scripts/migrations/migrate_002.py
```

---

## ⚠️ 注意事项

1. **生产环境谨慎执行**
   - 所有脚本在生产环境执行前请先备份
   - 优先在测试环境验证

2. **备份文件不要修改**
   - `backups/` 目录仅供历史参考
   - 不要基于备份文件进行开发

3. **修复脚本一次性使用**
   - `fixes/` 中的脚本通常针对特定问题
   - 问题解决后不需重复执行

4. **迁移脚本按顺序**
   - `migrations/` 脚本有依赖关系
   - 必须按时间戳顺序执行

---

## 📋 维护规范

### 添加新脚本
```bash
# 根据功能放入对应目录
# 管理功能 → admin/
# 修复问题 → fixes/
# 数据迁移 → migrations/
# 系统检查 → checks/
# 临时测试 → tests/
# 系统更新 → updates/
```

### 命名规范
```
admin/      : <动作>_<对象>.py    (例: create_admin.py)
fixes/      : fix_<问题>.py       (例: fix_database_schema.py)
checks/     : check_<对象>.py     (例: check_api_health.py)
migrations/ : migrate_<版本>.py   (例: migrate_20260823.py)
tests/      : test_<功能>.py      (例: test_integration.py)
updates/    : update_<模块>.py    (例: update_knowledge_api.py)
```

### 清理规则
- 已失效的修复脚本 → 移至 `backups/`
- 已完成的迁移 → 保留记录但添加注释
- 临时测试脚本 → 验证后移至 `backups/`

---

## 📚 相关文档

- [项目结构审计报告](../docs/archive/PROJECT_STRUCTURE_AUDIT_REPORT.md)
- [P0 清理完成报告](../docs/archive/P0_CLEANUP_REPORT.md)
- [项目归档文档](../docs/archive/CODEX_PROJECT_ARCHIVE.md)

---

**最后更新**: 2026-08-23  
**维护者**: LiuHao AI-OS Team
