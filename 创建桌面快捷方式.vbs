Set WshShell = CreateObject("WScript.Shell")

' 获取桌面路径
DesktopPath = WshShell.SpecialFolders("Desktop")

' 创建快捷方式
Set shortcut = WshShell.CreateShortcut(DesktopPath & "\鎏灏AI-OS.lnk")

' 设置快捷方式属性
shortcut.TargetPath = "D:\LiuHao-AI-OS\启动鎏灏AI.bat"
shortcut.WorkingDirectory = "D:\LiuHao-AI-OS"
shortcut.Description = "鎏灏 AI-OS CEO 控制台"
shortcut.IconLocation = "C:\Windows\System32\shell32.dll,238"

' 保存快捷方式
shortcut.Save

' 显示完成消息
MsgBox "✅ 桌面快捷方式已创建！" & vbCrLf & vbCrLf & "双击桌面上的【鎏灏AI-OS】图标即可启动系统", vbInformation, "创建成功"
