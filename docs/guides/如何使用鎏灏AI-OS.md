# 鎏灏 AI OS Y1.0 使用指南

## 一、系统简介

**鎏灏 AI OS Y1.0** 是一个企业级 AI 操作系统，为企业提供完整的 AI 能力管理、业务流程自动化和 CEO 指挥中心功能。

### 核心能力

- ✅ **安全与治理**：统一身份认证、权限管理、审批流程、审计日志
- ✅ **AI 运行时**：统一 AI Provider 网关、Agent 管理、AI 能力调度
- ✅ **知识管理**：企业知识库、公司大脑、记忆系统
- ✅ **工作流引擎**：任务编排、自动化执行、状态管理
- ✅ **AI 员工层**：AI 员工管理、岗位分配、绩效追踪
- ✅ **业务 OS**：销售、营销、客户开发、供应商管理
- ✅ **CEO 指挥中心**：全系统可视化、决策支持、实时监控

---

## 二、系统启动

### 方式一：生产环境启动（推荐）

```powershell
# 进入项目目录
cd D:\LiuHao-AI-OS

# 启动生产服务器
python start_production_single.py
```

服务将在 **http://localhost:8000** 启动。

### 方式二：开发环境启动

```powershell
# 进入项目目录
cd D:\LiuHao-AI-OS

# 激活虚拟环境（如果有）
.\.venv\Scripts\Activate

# 启动开发服务器
python start_development.py
```

### 验证服务状态

```powershell
# 检查健康状态
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health/" -UseBasicParsing
```

正常响应：
```json
{
  "status": "healthy",
  "timestamp": "2026-08-22T06:00:00.000000Z",
  "version": "1.0.0"
}
```

---

## 三、用户登录

### 默认管理员账号

- **用户名**：`admin`
- **密码**：`admin123`
- **角色**：`ADMIN` (系统管理员)

### 登录 API

```powershell
# 获取访问令牌
$body = @{ 
    username = "admin"
    password = "admin123" 
} | ConvertTo-Json

$response = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $body `
    -UseBasicParsing

# 提取令牌
$token = ($response.Content | ConvertFrom-Json).access_token

# 保存令牌供后续使用
$headers = @{ "Authorization" = "Bearer $token" }
```

### 登录响应

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 四、API 端点总览

### 4.1 认证与用户管理

#### 登录
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

#### 查看当前用户信息
```http
GET /api/v1/auth/me
Authorization: Bearer {token}
```

#### 用户列表
```http
GET /api/v1/users?limit=100
Authorization: Bearer {token}
```

#### 查看指定用户
```http
GET /api/v1/users/{user_id}
Authorization: Bearer {token}
```

#### 修改用户角色
```http
PATCH /api/v1/users/{user_id}/role
Authorization: Bearer {token}
Content-Type: application/json

{
  "role": "ADMIN"
}
```

#### 禁用/启用用户
```http
PATCH /api/v1/users/{user_id}/status
Authorization: Bearer {token}
Content-Type: application/json

{
  "is_active": false
}
```

---

### 4.2 角色与权限管理

#### 角色列表
```http
GET /api/v1/roles
Authorization: Bearer {token}
```

#### 创建角色
```http
POST /api/v1/roles
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "项目经理",
  "code": "PROJECT_MANAGER",
  "description": "负责项目管理",
  "permissions": ["project:read", "project:write"]
}
```

#### 分配权限到角色
```http
POST /api/v1/roles/{role_id}/permissions
Authorization: Bearer {token}
Content-Type: application/json

{
  "permission": "task:execute"
}
```

---

### 4.3 审批管理

#### 创建审批请求
```http
POST /api/v1/approvals
Authorization: Bearer {token}
Content-Type: application/json

{
  "request_type": "HIGH_RISK_OPERATION",
  "target_resource": "provider",
  "target_action": "call_external_api",
  "target_id": "openai-gpt4",
  "reason": "需要调用 GPT-4 分析市场数据",
  "payload": {
    "model": "gpt-4",
    "max_tokens": 2000
  }
}
```

#### 查看待审批列表
```http
GET /api/v1/approvals/pending
Authorization: Bearer {token}
```

#### 批准审批请求
```http
POST /api/v1/approvals/{request_id}/approve
Authorization: Bearer {token}
Content-Type: application/json

{
  "comment": "批准此次 API 调用"
}
```

#### 拒绝审批请求
```http
POST /api/v1/approvals/{request_id}/reject
Authorization: Bearer {token}
Content-Type: application/json

{
  "comment": "Token 额度不足，暂不批准"
}
```

---

### 4.4 AI Provider 管理

#### Provider 列表
```http
GET /api/v1/providers
Authorization: Bearer {token}
```

#### 查看 Provider 详情
```http
GET /api/v1/providers/{provider_id}
Authorization: Bearer {token}
```

#### 调用 AI Provider
```http
POST /api/v1/providers/{provider_id}/invoke
Authorization: Bearer {token}
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "分析2026年AI市场趋势"}
  ],
  "temperature": 0.7
}
```

---

### 4.5 AI Agent 管理

#### Agent 列表
```http
GET /api/v1/agents
Authorization: Bearer {token}
```

#### 创建 Agent
```http
POST /api/v1/agents
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "市场分析师",
  "type": "ANALYST",
  "provider_id": "openai-gpt4",
  "config": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

#### 执行 Agent 任务
```http
POST /api/v1/agents/{agent_id}/execute
Authorization: Bearer {token}
Content-Type: application/json

{
  "task": "分析竞争对手最新产品特性",
  "context": {
    "competitor": "Company X",
    "product": "Product Y"
  }
}
```

---

### 4.6 Workflow 管理

#### Workflow 列表
```http
GET /api/v1/workflows
Authorization: Bearer {token}
```

#### 创建 Workflow
```http
POST /api/v1/workflows
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "客户开发流程",
  "description": "自动化客户开发和跟进",
  "steps": [
    {
      "name": "线索收集",
      "agent_id": "research-agent",
      "action": "collect_leads"
    },
    {
      "name": "初步评估",
      "agent_id": "analyst-agent",
      "action": "evaluate_leads"
    },
    {
      "name": "联系客户",
      "agent_id": "sales-agent",
      "action": "contact_customer"
    }
  ]
}
```

#### 执行 Workflow
```http
POST /api/v1/workflows/{workflow_id}/execute
Authorization: Bearer {token}
Content-Type: application/json

{
  "input": {
    "target_industry": "AI SaaS",
    "region": "North America"
  }
}
```

---

### 4.7 AI 员工管理

#### AI 员工列表
```http
GET /api/v1/employees
Authorization: Bearer {token}
```

#### 创建 AI 员工
```http
POST /api/v1/employees
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "张三（AI销售）",
  "department": "SALES",
  "position": "销售代表",
  "description": "负责北美市场客户开发",
  "agent_type": "SALES_AGENT",
  "provider": "openai-gpt4"
}
```

#### 查看 AI 员工详情
```http
GET /api/v1/employees/{employee_id}
Authorization: Bearer {token}
```

#### 查看 AI 员工绩效
```http
GET /api/v1/employees/{employee_id}/performance
Authorization: Bearer {token}
```

#### 激活 AI 员工
```http
POST /api/v1/employees/{employee_id}/activate
Authorization: Bearer {token}
```

#### 暂停 AI 员工
```http
POST /api/v1/employees/{employee_id}/suspend
Authorization: Bearer {token}
```

---

### 4.8 业务任务管理

#### 业务任务列表
```http
GET /api/v1/business/tasks
Authorization: Bearer {token}
```

#### 创建业务任务
```http
POST /api/v1/business/tasks
Authorization: Bearer {token}
Content-Type: application/json

{
  "type": "CUSTOMER_DEVELOPMENT",
  "title": "开发美国 AI SaaS 客户",
  "description": "目标：获取 10 个 qualified leads",
  "priority": "HIGH",
  "assigned_to": "sales-ai-employee-001",
  "deadline": "2026-09-01T00:00:00Z"
}
```

#### 查看任务详情
```http
GET /api/v1/business/tasks/{task_id}
Authorization: Bearer {token}
```

#### 执行任务
```http
POST /api/v1/business/tasks/{task_id}/execute
Authorization: Bearer {token}
```

---

### 4.9 CEO 指挥中心

#### 完整仪表板
```http
GET /api/v1/ceo/dashboard?time_range_hours=24
Authorization: Bearer {token}
```

**响应示例**：
```json
{
  "timestamp": "2026-08-22T06:00:00.000000Z",
  "system": {
    "status": "healthy",
    "uptime_hours": 168.0,
    "total_users": 10,
    "active_sessions": 5,
    "cpu_usage_percent": 25.0,
    "memory_usage_percent": 40.0,
    "disk_usage_percent": 50.0
  },
  "business": {
    "total_tasks": 150,
    "completed_tasks": 120,
    "failed_tasks": 5,
    "in_progress_tasks": 25,
    "success_rate": 80.0,
    "avg_completion_time_hours": 2.5,
    "revenue_impact": 50000.0
  },
  "ai_team": {
    "total_employees": 12,
    "active_employees": 10,
    "suspended_employees": 2,
    "total_tasks_completed": 1500,
    "avg_tasks_per_employee": 125.0,
    "top_performers": [
      {
        "employee_id": "emp-001",
        "name": "GPT销售员工",
        "tasks_completed": 300,
        "success_rate": 95.0
      }
    ]
  },
  "tasks": {
    "total_tasks": 200,
    "pending_tasks": 30,
    "running_tasks": 20,
    "completed_tasks": 140,
    "failed_tasks": 10
  },
  "approvals": {
    "total_requests": 50,
    "pending_requests": 5,
    "approved_requests": 40,
    "rejected_requests": 5,
    "avg_approval_time_hours": 1.5
  }
}
```

#### 系统概览
```http
GET /api/v1/ceo/system
Authorization: Bearer {token}
```

#### 业务概览
```http
GET /api/v1/ceo/business?time_range_hours=24
Authorization: Bearer {token}
```

#### AI 团队概览
```http
GET /api/v1/ceo/ai-team
Authorization: Bearer {token}
```

#### 任务概览
```http
GET /api/v1/ceo/tasks?time_range_hours=24
Authorization: Bearer {token}
```

#### 审批概览
```http
GET /api/v1/ceo/approvals
Authorization: Bearer {token}
```

---

## 五、PowerShell 使用示例

### 5.1 完整登录流程

```powershell
# 1. 登录获取令牌
$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $loginBody `
    -UseBasicParsing

$token = ($loginResponse.Content | ConvertFrom-Json).access_token
$headers = @{ "Authorization" = "Bearer $token" }

Write-Host "✓ 登录成功，Token: $($token.Substring(0,50))..."

# 2. 查看当前用户信息
$meResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/me" `
    -Headers $headers `
    -UseBasicParsing

$meResponse.Content | ConvertFrom-Json | Format-List

# 3. 查看 CEO Dashboard
$dashboardResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/ceo/dashboard" `
    -Headers $headers `
    -UseBasicParsing

$dashboardResponse.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### 5.2 创建 AI 员工

```powershell
# 先登录
$loginBody = @{
    username = "admin"
    password = "admin123"
} | ConvertTo-Json

$loginResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Headers @{"Content-Type"="application/json"} `
    -Body $loginBody `
    -UseBasicParsing

$token = ($loginResponse.Content | ConvertFrom-Json).access_token
$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# 创建 AI 员工
$employeeBody = @{
    name = "李明（AI市场分析师）"
    department = "MARKETING"
    position = "市场分析师"
    description = "负责市场趋势分析和竞品研究"
    agent_type = "ANALYST"
    provider = "openai-gpt4"
} | ConvertTo-Json

$employeeResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/employees" `
    -Method POST `
    -Headers $headers `
    -Body $employeeBody `
    -UseBasicParsing

Write-Host "✓ AI员工创建成功："
$employeeResponse.Content | ConvertFrom-Json | Format-List
```

### 5.3 创建并执行 Workflow

```powershell
# 先登录
$token = "..." # 从上面的登录流程获取

$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# 创建 Workflow
$workflowBody = @{
    name = "每日市场报告"
    description = "自动收集和分析每日市场数据"
    steps = @(
        @{
            name = "数据收集"
            agent_id = "research-agent-001"
            action = "collect_market_data"
        },
        @{
            name = "数据分析"
            agent_id = "analyst-agent-001"
            action = "analyze_trends"
        },
        @{
            name = "生成报告"
            agent_id = "report-agent-001"
            action = "generate_report"
        }
    )
} | ConvertTo-Json -Depth 10

$workflowResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/workflows" `
    -Method POST `
    -Headers $headers `
    -Body $workflowBody `
    -UseBasicParsing

$workflowId = ($workflowResponse.Content | ConvertFrom-Json).id
Write-Host "✓ Workflow 创建成功，ID: $workflowId"

# 执行 Workflow
$executeBody = @{
    input = @{
        target_markets = @("美国", "欧洲", "亚洲")
        date_range = "2026-08-21"
    }
} | ConvertTo-Json -Depth 10

$executeResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/workflows/$workflowId/execute" `
    -Method POST `
    -Headers $headers `
    -Body $executeBody `
    -UseBasicParsing

Write-Host "✓ Workflow 执行成功："
$executeResponse.Content | ConvertFrom-Json | Format-List
```

---

## 六、常见使用场景

### 6.1 CEO 每日晨会

```powershell
# 获取过去 24 小时的完整报告
$token = "..." # 登录获取

$headers = @{ "Authorization" = "Bearer $token" }

# 查看完整仪表板
$dashboard = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/ceo/dashboard?time_range_hours=24" `
    -Headers $headers `
    -UseBasicParsing | 
    ConvertFrom-Json

Write-Host "`n========== 系统状态 =========="
Write-Host "状态: $($dashboard.system.status)"
Write-Host "运行时间: $($dashboard.system.uptime_hours) 小时"
Write-Host "用户总数: $($dashboard.system.total_users)"

Write-Host "`n========== 业务数据 =========="
Write-Host "总任务数: $($dashboard.business.total_tasks)"
Write-Host "完成任务: $($dashboard.business.completed_tasks)"
Write-Host "成功率: $($dashboard.business.success_rate)%"
Write-Host "收入影响: ¥$($dashboard.business.revenue_impact)"

Write-Host "`n========== AI 团队 =========="
Write-Host "AI员工总数: $($dashboard.ai_team.total_employees)"
Write-Host "活跃员工: $($dashboard.ai_team.active_employees)"
Write-Host "完成任务: $($dashboard.ai_team.total_tasks_completed)"

Write-Host "`n========== 待处理审批 =========="
Write-Host "待审批数: $($dashboard.approvals.pending_requests)"
```

### 6.2 批量创建 AI 员工

```powershell
$token = "..." # 登录获取

$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

# AI 员工配置
$employees = @(
    @{
        name = "王芳（AI销售）"
        department = "SALES"
        position = "销售代表"
        agent_type = "SALES_AGENT"
        provider = "openai-gpt4"
    },
    @{
        name = "刘强（AI市场）"
        department = "MARKETING"
        position = "SEO专家"
        agent_type = "MARKETING_AGENT"
        provider = "claude-3"
    },
    @{
        name = "陈静（AI研究）"
        department = "RESEARCH"
        position = "市场研究员"
        agent_type = "RESEARCH_AGENT"
        provider = "gemini-pro"
    }
)

foreach ($emp in $employees) {
    $body = $emp | ConvertTo-Json
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/api/v1/employees" `
        -Method POST `
        -Headers $headers `
        -Body $body `
        -UseBasicParsing
    
    $created = $response.Content | ConvertFrom-Json
    Write-Host "✓ 创建成功: $($created.name) - ID: $($created.id)"
}
```

### 6.3 查看 AI 员工绩效排名

```powershell
$token = "..." # 登录获取

$headers = @{ "Authorization" = "Bearer $token" }

# 获取 AI 团队概览
$aiTeam = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/ceo/ai-team" `
    -Headers $headers `
    -UseBasicParsing |
    ConvertFrom-Json

Write-Host "`n========== AI员工绩效排名 =========="
Write-Host "排名`t员工名称`t`t完成任务`t成功率"
Write-Host "----`t--------`t`t--------`t------"

$rank = 1
foreach ($performer in $aiTeam.top_performers) {
    Write-Host "$rank`t$($performer.name)`t`t$($performer.tasks_completed)`t`t$($performer.success_rate)%"
    $rank++
}
```

---

## 七、权限说明

### 7.1 系统角色

| 角色 | 权限范围 | 适用场景 |
|------|---------|---------|
| **ADMIN** | 所有权限 | CEO、CTO、系统管理员 |
| **MANAGER** | 业务管理、员工管理、审批 | 部门经理、项目经理 |
| **USER** | 基础操作、查看数据 | 普通员工 |
| **VIEWER** | 只读权限 | 审计员、观察者 |

### 7.2 权限列表

#### 系统管理
- `SYSTEM_ADMIN` - 系统管理员（完全控制）
- `USER_READ` - 查看用户
- `USER_WRITE` - 创建/修改用户
- `ROLE_MANAGE` - 管理角色

#### 业务操作
- `TASK_READ` - 查看任务
- `TASK_WRITE` - 创建/修改任务
- `TASK_EXECUTE` - 执行任务
- `WORKFLOW_READ` - 查看工作流
- `WORKFLOW_WRITE` - 创建/修改工作流

#### AI 管理
- `AGENT_READ` - 查看 Agent
- `AGENT_WRITE` - 创建/修改 Agent
- `PROVIDER_READ` - 查看 Provider
- `PROVIDER_CALL` - 调用 Provider API

#### 审批管理
- `APPROVAL_CREATE` - 创建审批请求
- `APPROVAL_APPROVE` - 批准审批
- `APPROVAL_REJECT` - 拒绝审批

---

## 八、安全最佳实践

### 8.1 密码管理

生产环境中，请立即修改默认密码：

```powershell
# 修改 admin 密码
$token = "..." # 登录获取

$headers = @{ 
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$passwordBody = @{
    old_password = "admin123"
    new_password = "YourStrongPassword@2026"
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/change-password" `
    -Method POST `
    -Headers $headers `
    -Body $passwordBody `
    -UseBasicParsing
```

### 8.2 API Key 管理

- ✅ 所有 Provider API Key 存储在 `.env.production` 中
- ✅ 禁止将 API Key 硬编码在代码中
- ✅ 禁止将 API Key 提交到 Git
- ✅ 定期轮换 API Key

### 8.3 审批流程

高风险操作必须经过审批：

- ✅ 调用昂贵的 AI 模型（如 GPT-4）
- ✅ 修改系统配置
- ✅ 批量数据操作
- ✅ 外部 API 调用

---

## 九、故障排查

### 9.1 无法启动服务

**问题**：运行 `python start_production_single.py` 无响应

**解决**：
```powershell
# 检查端口占用
netstat -ano | findstr :8000

# 如果端口被占用，终止进程
taskkill /PID <PID> /F

# 重新启动
python start_production_single.py
```

### 9.2 登录失败

**问题**：返回 `401 Unauthorized`

**解决**：
```powershell
# 1. 确认密码正确（默认：admin123）
# 2. 检查数据库中的用户
cd D:\LiuHao-AI-OS
sqlite3 liuhao_ai_os_production.db "SELECT id, username, is_active FROM users;"

# 3. 如果密码错误，重置密码
python -c "
import bcrypt
password = 'admin123'
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
print(hashed.decode())
"
# 将生成的哈希值更新到数据库中
```

### 9.3 CEO Dashboard 返回 403

**问题**：访问 `/api/v1/ceo/dashboard` 返回权限不足

**解决**：
```powershell
# 确认用户角色为 ADMIN
$token = "..." # 登录获取
$headers = @{ "Authorization" = "Bearer $token" }

$meResponse = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/v1/auth/me" `
    -Headers $headers `
    -UseBasicParsing

$meResponse.Content | ConvertFrom-Json | Select-Object role

# 如果角色不是 ADMIN，修改角色
# （需要其他 ADMIN 用户执行）
```

---

## 十、下一步

### 10.1 配置 AI Providers

编辑 `.env.production` 添加您的 API Keys：

```env
# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-claude-key

# Google Gemini
GOOGLE_API_KEY=your-gemini-key

# xAI Grok
XAI_API_KEY=your-xai-key

# DeepSeek
DEEPSEEK_API_KEY=your-deepseek-key

# Moonshot Kimi
MOONSHOT_API_KEY=your-moonshot-key
```

### 10.2 创建您的第一个 AI 员工

参考 [5.2 创建 AI 员工](#52-创建-ai-员工) 创建您的第一个 AI 员工。

### 10.3 设计您的第一个 Workflow

参考 [5.3 创建并执行 Workflow](#53-创建并执行-workflow) 创建自动化流程。

---

## 十一、技术支持

### 项目地址
- 本地路径：`D:\LiuHao-AI-OS`
- API 文档：http://localhost:8000/docs （Swagger UI）
- 架构文档：`D:\LiuHao-AI-OS\docs\`

### 日志位置
- 生产日志：`D:\LiuHao-AI-OS\logs\production.log`
- 错误日志：`D:\LiuHao-AI-OS\logs\error.log`

---

## 十二、版本信息

- **系统版本**：LiuHao AI OS Y1.0
- **完成阶段**：
  - ✅ Stage 1: Core + Security
  - ✅ Stage 2: Identity + Governance
  - ✅ Stage 3: AI Brain
  - ✅ Stage 4: Knowledge + Company Brain
  - ✅ Stage 5: Workflow + Execution
  - ✅ Stage 6: AI Workforce
  - ✅ Stage 7: Business OS
  - ✅ Stage 8: CEO AI OS

- **最后更新**：2026-08-22

---

**恭喜！您现在已经可以开始使用鎏灏 AI OS Y1.0 了。**

如需帮助，请查看项目文档或联系技术支持。
