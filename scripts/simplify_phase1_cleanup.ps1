# 鎏灏 AI-OS 精简脚本 - Phase 1
# 方案 A：激进精简 (27表 → 15表)
# 生成时间: 2026-08-24 00:00

Write-Host "🚀 开始执行激进精简方案..." -ForegroundColor Green
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectRoot = "D:\LiuHao-AI-OS"

Set-Location $ProjectRoot

# ============================================================
# Step 1: 删除 multi_tenant 模块 (1,690行 + 6表)
# ============================================================
Write-Host "📦 Step 1: 删除 multi_tenant 模块..." -ForegroundColor Yellow

$MultiTenantFiles = @(
    "src/multi_tenant/__init__.py",
    "src/multi_tenant/api.py",
    "src/multi_tenant/master_password.py",
    "src/multi_tenant/migration.py",
    "src/multi_tenant/models.py",
    "src/multi_tenant/services.py",
    "src/api/routes/master_account.py"
)

foreach ($file in $MultiTenantFiles) {
    if (Test-Path $file) {
        Write-Host "  ❌ 删除: $file"
        Remove-Item -Force $file
    }
}

# 删除目录
if (Test-Path "src/multi_tenant") {
    Remove-Item -Recurse -Force "src/multi_tenant"
    Write-Host "  ❌ 删除目录: src/multi_tenant"
}

if (Test-Path "tests/multi_tenant") {
    Remove-Item -Recurse -Force "tests/multi_tenant"
    Write-Host "  ❌ 删除目录: tests/multi_tenant"
}

Write-Host "  ✅ multi_tenant 模块已删除 (-1,690行, -6表)" -ForegroundColor Green
Write-Host ""

# ============================================================
# Step 2: 删除 governance 模块 (466行)
# ============================================================
Write-Host "📦 Step 2: 删除 governance 模块..." -ForegroundColor Yellow

$GovernanceFiles = @(
    "src/governance/__init__.py",
    "src/governance/approval.py",
    "src/governance/risk.py",
    "src/api/routes/approvals.py"
)

foreach ($file in $GovernanceFiles) {
    if (Test-Path $file) {
        Write-Host "  ❌ 删除: $file"
        Remove-Item -Force $file
    }
}

# 删除目录
if (Test-Path "src/governance") {
    Remove-Item -Recurse -Force "src/governance"
    Write-Host "  ❌ 删除目录: src/governance"
}

if (Test-Path "tests/governance") {
    Remove-Item -Recurse -Force "tests/governance"
    Write-Host "  ❌ 删除目录: tests/governance"
}

Write-Host "  ✅ governance 模块已删除 (-466行)" -ForegroundColor Green
Write-Host ""

# ============================================================
# Step 3: 清理依赖引用
# ============================================================
Write-Host "📦 Step 3: 清理依赖引用..." -ForegroundColor Yellow

$FilesToUpdate = @(
    "src/ceo/dashboard.py",
    "src/api/routes/ceo.py",
    "src/api/routes/users.py",
    "src/api/dependencies/approval.py",
    "src/ai/tools.py",
    "src/database/models.py"
)

Write-Host "  ⚠️ 需要手动检查以下文件并移除 governance/multi_tenant 引用:" -ForegroundColor Cyan
foreach ($file in $FilesToUpdate) {
    if (Test-Path $file) {
        Write-Host "    - $file"
    }
}

Write-Host ""

# ============================================================
# Step 4: 统计结果
# ============================================================
Write-Host "📊 精简统计..." -ForegroundColor Yellow

$RemainingFiles = (Get-ChildItem src -Recurse -Filter "*.py" | Measure-Object).Count
$RemainingLines = (Get-ChildItem src -Recurse -Filter "*.py" | Get-Content | Measure-Object -Line).Lines

Write-Host "  当前 Python 文件数: $RemainingFiles"
Write-Host "  当前代码行数: $RemainingLines"
Write-Host ""

# ============================================================
# Step 5: 运行测试
# ============================================================
Write-Host "🧪 Step 5: 运行测试检查..." -ForegroundColor Yellow
Write-Host "  执行: pytest tests/ -v --tb=short" -ForegroundColor Cyan
Write-Host "  (需要手动运行以验证删除后的影响)" -ForegroundColor Gray
Write-Host ""

# ============================================================
# 完成
# ============================================================
Write-Host "✅ Phase 1 清理完成！" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️ 后续步骤:" -ForegroundColor Yellow
Write-Host "  1. 运行: pytest tests/ -v"
Write-Host "  2. 检查并修复依赖引用"
Write-Host "  3. 执行 Phase 2: 数据模型合并"
Write-Host "  4. 生成新的 migration"
Write-Host ""
