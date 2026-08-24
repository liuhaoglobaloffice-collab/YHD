@echo off
chcp 65001 >nul
color 0A
title 鎏灏 AI-OS - 启动中...

echo.
echo ============================================================
echo                  🚀 鎏灏 AI-OS 启动程序
echo ============================================================
echo.
echo [1/4] 检查环境...

cd /d D:\LiuHao-AI-OS

echo [2/4] 启动后端服务...
start "鎏灏后端API" /MIN cmd /c "python -m uvicorn src.main:app --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

echo [3/4] 启动前端服务...
cd frontend
start "鎏灏前端UI" /MIN cmd /c "npm run dev"
timeout /t 5 /nobreak >nul

echo [4/4] 打开应用...
timeout /t 3 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo ============================================================
echo ✅ 鎏灏 AI-OS 已启动成功！
echo.
echo 📱 前端: http://localhost:3000
echo 🔌 后端: http://localhost:8000
echo.
echo 账号: 1163661699
echo 密码: yhd2579..lq
echo.
echo 💡 关闭此窗口将停止所有服务
echo ============================================================
echo.

pause
