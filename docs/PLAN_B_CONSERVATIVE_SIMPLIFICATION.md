# 📋 鎏灏 AI-OS - 方案 B：保守精简执行计划

**生成时间**: 2026-08-24 00:08  
**方案**: 保守精简 (27表 → 21表)  
**策略**: 仅删除 multi_tenant 模块，保留其他所有模块

---

## 🎯 精简目标

**删除内容**:
- ❌ **multi_tenant 模块** (1,690 行代码 + 6 个数据表)

**保留内容**:
- ✅ governance 模块 (审批流程)
- ✅ identity 模块 (6表完整)
- ✅ knowledge 模块 (4表完整)
- ✅ workforce 模块 (3表完整)
- ✅ 所有其他模块

**预期效果**:
- 模块数: 17 → 16 (-1个)
- 数据表: 27 → 21 (-6个)
- 代码行: 28,586 → ~26,900 (-1,690行)
- 节省时间: **2 周**
- 上线日期: **2027-01-03** (提前 20 天)

---

## 📦 Step 1: 备份项目 (可选但推荐)

```powershell
# 创建备份目录
cd D:\LiuHao-AI-OS
$BackupDir = "D:\LiuHao-AI-OS-Backup-$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -Path "D:\LiuHao-AI-OS" -Destination $BackupDir -Recurse
Write-Host "备份完成: $BackupDir"
```

---

## 🗑️ Step 2: 删除 multi_tenant 模块

### 2.1 删除的文件清单

**模块文件** (6 个):
```
src/multi_tenant/__init__.py
src/multi_tenant/api.py
src/multi_tenant/master_password.py
src/multi_tenant/migration.py
src/multi_tenant/models.py
src/multi_tenant/services.py
```

**API 路由文件** (1 个):
```
src/api/routes/master_account.py
```

**测试文件** (整个目录):
```
tests/multi_tenant/
```

### 2.2 删除的数据表 (6 个)

| 表名 | 用途 | 代码位置 |
|------|------|----------|
| `Account` | 租户账户 | src/multi_tenant/models.py:35 |
| `APIConfiguration` | API配置 | src/multi_tenant/models.py:80 |
| `TokenUsageStats` | Token统计 | src/multi_tenant/models.py:115 |
| `TokenConsumptionLog` | Token日志 | src/multi_tenant/models.py:145 |
| `MasterStealthPermission` | 隐秘权限 | src/multi_tenant/models.py:175 |
| `MasterStealthOperation` | 隐秘操作 | src/multi_tenant/models.py:205 |

### 2.3 执行删除命令

```powershell
# 切换到项目目录
cd D:\LiuHao-AI-OS

# 删除 multi_tenant 模块
Remove-Item -Recurse -Force src\multi_tenant

# 删除 multi_tenant 测试
if (Test-Path tests\multi_tenant) {
    Remove-Item -Recurse -Force tests\multi_tenant
}

# 删除 master_account API 路由
if (Test-Path src\api\routes\master_account.py) {
    Remove-Item -Force src\api\routes\master_account.py
}

# 验证删除
Get-ChildItem src -Directory | Where-Object { $_.Name -eq 'multi_tenant' }
# 应该返回空结果
```

---

## 📝 Step 3: 更新依赖引用

### 3.1 需要修改的文件

| 文件 | 问题 | 操作 |
|------|------|------|
| `src/database/models.py` | 注释提到 multi_tenant | 删除相关注释 |

### 3.2 更新 `src/database/models.py`

找到这一行:
```python
Note: Models from other modules (identity, multi_tenant, supplier)
```

改为:
```python
Note: Models from other modules (identity, supplier)
```

---

## 🔍 Step 4: 检查其他依赖

### 4.1 搜索 multi_tenant 引用

```powershell
cd D:\LiuHao-AI-OS

# 搜索所有 multi_tenant 导入
rg 'from.*multi_tenant|import.*multi_tenant' src/ -l

# 应该返回以下文件 (需要检查):
# src/database/models.py  ← Step 3 已处理
```

### 4.2 如果发现其他引用

如果搜索结果还有其他文件，需要逐个检查并移除对 `multi_tenant` 的引用。

---

## 🗄️ Step 5: 生成数据库迁移

### 5.1 生成新的 migration

```powershell
cd D:\LiuHao-AI-OS

# 生成 migration
alembic revision --autogenerate -m "Remove multi_tenant module and tables"

# 检查生成的 migration 文件
Get-ChildItem alembic\versions -Filter "*.py" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

### 5.2 检查 migration 内容

打开最新的 migration 文件，确认它会删除这 6 个表：
- `accounts`
- `api_configurations`
- `token_usage_stats`
- `token_consumption_logs`
- `master_stealth_permissions`
- `master_stealth_operations`

### 5.3 应用 migration

```powershell
# 应用 migration
alembic upgrade head

# 验证表已删除
alembic current
```

---

## 🧪 Step 6: 运行测试验证

### 6.1 运行完整测试

```powershell
cd D:\LiuHao-AI-OS

# 运行所有测试
pytest tests/ -v --tb=short

# 预期结果:
# - 测试通过率: 保持 92%+
# - 失败测试应该只是因为 multi_tenant 模块被删除
```

### 6.2 运行覆盖率测试

```powershell
# 运行覆盖率测试
pytest tests/ --cov=src --cov-report=term-missing

# 目标:
# - 代码覆盖率: 85%+
```

### 6.3 检查是否有导入错误

```powershell
# 检查所有文件是否能正常导入
python -m src.main --help
```

---

## 📊 Step 7: 验证精简效果

### 7.1 统计代码行数

```powershell
cd D:\LiuHao-AI-OS

# 统计当前代码行数
$Lines = (Get-ChildItem src -Recurse -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
Write-Host "当前代码行数: $Lines"

# 预期: ~26,900 行 (删除前: 28,586 行)
```

### 7.2 统计模块数

```powershell
# 统计模块数
(Get-ChildItem src -Directory | Where-Object { $_.Name -ne '__pycache__' }).Count

# 预期: 16 个 (删除前: 17 个)
```

### 7.3 统计数据表数

```powershell
# 搜索数据模型
rg "^class.*\(Base\):" src/ -g "models.py" | Measure-Object -Line

# 预期: 21 个表 (删除前: 27 个)
```

---

## 📄 Step 8: 更新文档

### 8.1 需要更新的文档

- `docs/FINAL_ROADMAP_12WEEKS.md` - 确认多租户已删除
- `docs/MODULE_COMPLETION_AND_SIMPLIFICATION_REPORT.md` - 更新模块状态
- `README.md` - 更新架构图（如果有）
- `docs/core/DATABASE_SCHEMA.md` - 更新数据库 ERD 图

### 8.2 创建精简报告

```powershell
# 创建精简完成报告
New-Item -ItemType File -Path "docs/SIMPLIFICATION_COMPLETE_REPORT.md"
```

报告内容包括:
- 删除的模块和表
- 精简前后对比
- 测试结果
- 遇到的问题及解决方案

---

## ✅ 执行清单 (Checklist)

复制以下清单，执行时勾选：

```
方案 B 执行清单:

[ ] 1. 备份项目 (可选但推荐)
[ ] 2. 删除 src/multi_tenant 目录
[ ] 3. 删除 tests/multi_tenant 目录
[ ] 4. 删除 src/api/routes/master_account.py
[ ] 5. 更新 src/database/models.py (移除 multi_tenant 注释)
[ ] 6. 搜索并移除其他 multi_tenant 引用
[ ] 7. 生成新的 alembic migration
[ ] 8. 应用 alembic migration
[ ] 9. 运行 pytest 验证
[ ] 10. 检查代码覆盖率
[ ] 11. 统计精简效果
[ ] 12. 更新文档
[ ] 13. 提交代码 (git commit)
```

---

## 🚀 快速执行脚本 (一键删除)

将以下命令复制到 PowerShell 中执行：

```powershell
# === 鎏灏 AI-OS - 方案 B 快速删除脚本 ===
cd D:\LiuHao-AI-OS

Write-Host "🚀 开始执行方案 B..." -ForegroundColor Green

# Step 1: 删除模块
Write-Host "📦 删除 multi_tenant 模块..." -ForegroundColor Yellow
if (Test-Path src\multi_tenant) {
    Remove-Item -Recurse -Force src\multi_tenant
    Write-Host "  ✅ 已删除 src\multi_tenant" -ForegroundColor Green
}

if (Test-Path tests\multi_tenant) {
    Remove-Item -Recurse -Force tests\multi_tenant
    Write-Host "  ✅ 已删除 tests\multi_tenant" -ForegroundColor Green
}

if (Test-Path src\api\routes\master_account.py) {
    Remove-Item -Force src\api\routes\master_account.py
    Write-Host "  ✅ 已删除 src\api\routes\master_account.py" -ForegroundColor Green
}

# Step 2: 验证删除
Write-Host ""
Write-Host "🔍 验证删除..." -ForegroundColor Yellow
$MultiTenantExists = Test-Path src\multi_tenant
if (-not $MultiTenantExists) {
    Write-Host "  ✅ multi_tenant 模块已成功删除" -ForegroundColor Green
} else {
    Write-Host "  ⚠️ multi_tenant 模块仍然存在！" -ForegroundColor Red
}

# Step 3: 统计效果
Write-Host ""
Write-Host "📊 统计精简效果..." -ForegroundColor Yellow
$Lines = (Get-ChildItem src -Recurse -Filter "*.py" | Get-Content | Measure-Object -Line).Lines
$Modules = (Get-ChildItem src -Directory | Where-Object { $_.Name -ne '__pycache__' }).Count
Write-Host "  当前代码行数: $Lines" -ForegroundColor Cyan
Write-Host "  当前模块数: $Modules" -ForegroundColor Cyan

Write-Host ""
Write-Host "✅ 方案 B 删除完成！" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️ 后续步骤:" -ForegroundColor Yellow
Write-Host "  1. 更新 src/database/models.py (移除 multi_tenant 注释)"
Write-Host "  2. 生成 migration: alembic revision --autogenerate -m 'Remove multi_tenant'"
Write-Host "  3. 应用 migration: alembic upgrade head"
Write-Host "  4. 运行测试: pytest tests/ -v"
Write-Host ""
```

---

## 🎯 预期结果

执行完成后，你应该看到：

**✅ 成功指标**:
- `src/multi_tenant` 目录不存在
- `tests/multi_tenant` 目录不存在
- `src/api/routes/master_account.py` 不存在
- 代码行数: ~26,900 行
- 模块数: 16 个
- 数据表: 21 个
- 测试通过率: 92%+

**📅 时间线**:
- 执行时间: 0.5 天
- 测试修复: 0.5 天
- 总耗时: **1 天**
- 上线日期: **2027-01-03**

---

## 📞 遇到问题？

如果执行过程中遇到问题：

1. **删除失败** - 检查文件是否被占用，关闭 VS Code 或 PyCharm
2. **测试失败** - 检查是否还有其他文件引用 multi_tenant
3. **Migration 失败** - 检查数据库连接，备份数据库后重试

---

**执行时间**: 2026-08-24  
**预计完成**: 2026-08-25  
**责任人**: 开发工程师
