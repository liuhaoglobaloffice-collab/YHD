@echo off
chcp 65001 >nul
color 0B
title 创建桌面快捷方式

echo.
echo ============================================================
echo              🎯 鎏灏 AI-OS 桌面快捷方式生成器
echo ============================================================
echo.
echo 正在创建桌面快捷方式...
echo.

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\鎏灏AI-OS.lnk'); $Shortcut.TargetPath = 'D:\LiuHao-AI-OS\启动鎏灏AI.bat'; $Shortcut.WorkingDirectory = 'D:\LiuHao-AI-OS'; $Shortcut.Description = '鎏灏 AI-OS CEO 控制台 - 双击启动'; $Shortcut.IconLocation = 'C:\Windows\System32\shell32.dll,238'; $Shortcut.Save()"

echo ✅ 桌面快捷方式已创建成功！
echo.
echo 📍 快捷方式位置: 桌面\鎏灏AI-OS.lnk
echo.
echo 使用方法:
echo   1. 双击桌面上的"鎏灏AI-OS"图标
echo   2. 等待 10-15 秒启动
echo   3. 浏览器自动打开应用
echo   4. 输入账号: 1163661699
echo   5. 输入密码: yhd2579..lq
echo.
echo 💡 提示:
echo   - 右键图标可以固定到任务栏
echo   - 复制到启动文件夹可以开机自启
echo   - 右键属性可以设置快捷键
echo.
echo ============================================================
echo.
pause
