# 鎏灏 AI-OS 桌面启动器
# PowerShell 版本 - 带GUI界面

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 创建主窗口
$form = New-Object System.Windows.Forms.Form
$form.Text = '🚀 鎏灏 AI-OS 启动器'
$form.Size = New-Object System.Drawing.Size(500,400)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(15, 20, 51)
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false

# 标题
$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Location = New-Object System.Drawing.Point(50,30)
$lblTitle.Size = New-Object System.Drawing.Size(400,40)
$lblTitle.Text = '鎏灏 AI-OS'
$lblTitle.Font = New-Object System.Drawing.Font("Microsoft YaHei",24,[System.Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = [System.Drawing.Color]::Cyan
$lblTitle.TextAlign = 'MiddleCenter'
$form.Controls.Add($lblTitle)

# 副标题
$lblSubtitle = New-Object System.Windows.Forms.Label
$lblSubtitle.Location = New-Object System.Drawing.Point(50,75)
$lblSubtitle.Size = New-Object System.Drawing.Size(400,25)
$lblSubtitle.Text = 'CEO 智能控制台'
$lblSubtitle.Font = New-Object System.Drawing.Font("Microsoft YaHei",12)
$lblSubtitle.ForeColor = [System.Drawing.Color]::LightCyan
$lblSubtitle.TextAlign = 'MiddleCenter'
$form.Controls.Add($lblSubtitle)

# 状态标签
$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Location = New-Object System.Drawing.Point(50,130)
$lblStatus.Size = New-Object System.Drawing.Size(400,30)
$lblStatus.Text = '准备启动...'
$lblStatus.Font = New-Object System.Drawing.Font("Microsoft YaHei",11)
$lblStatus.ForeColor = [System.Drawing.Color]::White
$lblStatus.TextAlign = 'MiddleCenter'
$form.Controls.Add($lblStatus)

# 进度条
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(50,170)
$progressBar.Size = New-Object System.Drawing.Size(400,30)
$progressBar.Style = 'Continuous'
$form.Controls.Add($progressBar)

# 启动按钮
$btnStart = New-Object System.Windows.Forms.Button
$btnStart.Location = New-Object System.Drawing.Point(150,230)
$btnStart.Size = New-Object System.Drawing.Size(200,50)
$btnStart.Text = '🚀 启动系统'
$btnStart.Font = New-Object System.Drawing.Font("Microsoft YaHei",14,[System.Drawing.FontStyle]::Bold)
$btnStart.BackColor = [System.Drawing.Color]::DarkCyan
$btnStart.ForeColor = [System.Drawing.Color]::White
$btnStart.FlatStyle = 'Flat'
$btnStart.Cursor = 'Hand'
$form.Controls.Add($btnStart)

# 信息标签
$lblInfo = New-Object System.Windows.Forms.Label
$lblInfo.Location = New-Object System.Drawing.Point(50,300)
$lblInfo.Size = New-Object System.Drawing.Size(400,60)
$lblInfo.Text = "前端: http://localhost:3000`n后端: http://localhost:8000`n账号: 1163661699"
$lblInfo.Font = New-Object System.Drawing.Font("Microsoft YaHei",9)
$lblInfo.ForeColor = [System.Drawing.Color]::LightGray
$lblInfo.TextAlign = 'MiddleCenter'
$form.Controls.Add($lblInfo)

# 启动按钮点击事件
$btnStart.Add_Click({
    $btnStart.Enabled = $false
    $lblStatus.Text = '正在启动后端服务...'
    $progressBar.Value = 25
    
    # 启动后端
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c python -m uvicorn src.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "D:\LiuHao-AI-OS" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    
    $lblStatus.Text = '正在启动前端服务...'
    $progressBar.Value = 50
    
    # 启动前端
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "D:\LiuHao-AI-OS\frontend" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    
    $lblStatus.Text = '正在打开应用...'
    $progressBar.Value = 75
    
    # 打开浏览器
    Start-Process "http://localhost:3000"
    Start-Sleep -Seconds 2
    
    $lblStatus.Text = '✅ 启动成功！'
    $lblStatus.ForeColor = [System.Drawing.Color]::LightGreen
    $progressBar.Value = 100
    
    Start-Sleep -Seconds 2
    $form.Close()
})

# 显示窗口
[void]$form.ShowDialog()
