@echo off
chcp 65001 >nul
echo ========================================
echo   🎯 鎏灏 AI-OS - 阶段1验收启动脚本
echo ========================================
echo.
echo 正在启动前端开发服务器...
echo.

cd /d "%~dp0"

REM 检查Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Node.js，请先安装Node.js
    pause
    exit /b 1
)

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo ⚠️ 未找到node_modules，正在安装依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo ✅ 环境检查完成
echo.
echo ========================================
echo   🚀 前端服务器即将启动
echo ========================================
echo.
echo 📍 访问地址: http://localhost:3000/
echo 👤 管理员账号: admin
echo 🔑 密码: Admin2026
echo.
echo 💡 提示:
echo   - 按 Ctrl+C 可以停止服务器
echo   - 按 F12 打开浏览器开发者工具
echo   - 查看 STAGE1_GUIDE.md 了解验收清单
echo.
echo ========================================
echo.

REM 启动开发服务器
call npm run dev

pause
