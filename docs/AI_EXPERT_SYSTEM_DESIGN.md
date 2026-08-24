# 🤖 鎏灏 AI-OS - AI专家系统设计方案

**版本**: v1.0  
**创建时间**: 2026-08-24  
**状态**: ✅ 已确认  
**实施阶段**: Week 12-13

---

## 🎯 核心设计原则

### 你的明确要求 ⭐
> "我的32个IA专家，变成10个IA专家，后天可以自行添加，还有个添加IA专家那可以填写API的端口"

**设计方案**:
```yaml
初始配置:
  - 10个核心AI专家（预设）
  - 涵盖最常用的业务场景

扩展能力:
  - 最多支持32个AI专家
  - 通过UI界面添加新专家
  - 每个专家可以配置API端点
  - 支持多种LLM供应商

核心功能:
  ✅ 添加/删除专家（UI界面）
  ✅ 配置API端点和Key
  ✅ 启用/禁用专家
  ✅ 测试连接
  ✅ 专家性能监控
```

---

## 📋 10个核心AI专家（初始配置）

### 预设专家列表

| # | 专家名称 | 部门 | 核心能力 | 默认LLM |
|---|---------|------|---------|---------|
| 1 | **销售经理** | Sales | 客户开发、谈判策略、交易闭环 | GPT-4 |
| 2 | **客户开发专员** | Sales | 潜客挖掘、需求分析、关系维护 | Claude-3.5 |
| 3 | **风险管理专家** | Finance | 供应商评估、财务风险、合规审查 | GPT-4 |
| 4 | **供应链专家** | Operations | 供应商管理、物流优化、库存控制 | DeepSeek |
| 5 | **市场分析师** | Marketing | 市场调研、竞品分析、趋势预测 | Claude-3.5 |
| 6 | **法务顾问** | Legal | 合同审查、法律风险、知识产权 | GPT-4 |
| 7 | **财务分析师** | Finance | 财务建模、成本分析、利润优化 | DeepSeek |
| 8 | **数据分析师** | Data | 数据挖掘、报表生成、可视化 | Gemini-1.5 |
| 9 | **客服专家** | Support | 客户咨询、问题解决、满意度 | Kimi |
| 10 | **运营协调员** | Operations | 流程优化、任务协调、资源调度 | Claude-3.5 |

**覆盖场景**:
- ✅ 销售与客户管理（2个专家）
- ✅ 财务与风险控制（2个专家）
- ✅ 供应链与运营（2个专家）
- ✅ 市场与数据分析（2个专家）
- ✅ 法务与客服支持（2个专家）

---

## 🔌 API配置系统设计

### UI界面结构

```
/ceo-dashboard/ai-experts
├── /manage              # 专家管理主页
│   ├── 专家列表（10个预设 + 用户添加）
│   ├── 启用/禁用开关
│   ├── 性能监控
│   └── 操作按钮（编辑/删除/测试）
│
├── /add-new             # 添加新专家 ⭐
│   ├── 基本信息
│   │   ├── 专家名称 *
│   │   ├── 部门选择 *
│   │   ├── 专业领域 *
│   │   └── 描述
│   │
│   ├── API配置 ⭐
│   │   ├── LLM供应商（GPT-4/Claude/DeepSeek/Gemini/Kimi/Grok）
│   │   ├── API端点URL *
│   │   ├── API Key *
│   │   ├── 模型名称 *
│   │   ├── 温度参数（0-1）
│   │   ├── Max Tokens
│   │   └── 测试连接按钮
│   │
│   ├── 能力定义
│   │   ├── 核心能力（标签）
│   │   ├── 系统提示词 *
│   │   ├── 示例对话
│   │   └── 上下文长度
│   │
│   └── 高级设置
│       ├── 优先级（1-10）
│       ├── 并发限制
│       ├── 超时时间
│       └── 重试策略
│
└── /edit/{expert_id}    # 编辑专家
    └── （与添加页面相同结构）
```

---

## 💾 数据库设计

### 核心表结构

#### 1. `ai_expert_profiles` - 专家配置表
```sql
CREATE TABLE ai_expert_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 基本信息
    name VARCHAR(100) NOT NULL,              -- 专家名称 ⭐
    department VARCHAR(50) NOT NULL,         -- 部门
    specialization TEXT NOT NULL,            -- 专业领域
    description TEXT,                        -- 描述
    
    -- 类型标识
    is_builtin BOOLEAN DEFAULT FALSE,        -- 是否预设专家
    is_custom BOOLEAN DEFAULT TRUE,          -- 是否自定义
    
    -- 能力定义
    capabilities JSONB NOT NULL,             -- 核心能力列表
    system_prompt TEXT NOT NULL,             -- 系统提示词 ⭐
    example_conversations JSONB,             -- 示例对话
    
    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,         -- 是否启用
    priority INTEGER DEFAULT 5,              -- 优先级 (1-10)
    
    -- 性能配置
    max_concurrent_tasks INTEGER DEFAULT 3,  -- 最大并发
    timeout_seconds INTEGER DEFAULT 120,     -- 超时时间
    retry_strategy JSONB,                    -- 重试策略
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    -- 约束
    CONSTRAINT check_max_experts 
        CHECK ((SELECT COUNT(*) FROM ai_expert_profiles WHERE is_enabled = TRUE) <= 32)
);

-- 索引
CREATE INDEX idx_expert_department ON ai_expert_profiles(department);
CREATE INDEX idx_expert_enabled ON ai_expert_profiles(is_enabled);
CREATE INDEX idx_expert_builtin ON ai_expert_profiles(is_builtin);
```

#### 2. `ai_expert_api_configs` - API配置表 ⭐
```sql
CREATE TABLE ai_expert_api_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expert_id UUID NOT NULL REFERENCES ai_expert_profiles(id) ON DELETE CASCADE,
    
    -- LLM供应商配置 ⭐
    provider VARCHAR(50) NOT NULL,           -- GPT-4/Claude/DeepSeek/Gemini/Kimi/Grok
    api_endpoint VARCHAR(500) NOT NULL,      -- API端点URL ⭐
    api_key_encrypted TEXT NOT NULL,         -- 加密的API Key ⭐
    model_name VARCHAR(100) NOT NULL,        -- 模型名称 (gpt-4-turbo, claude-3.5-sonnet等)
    
    -- 模型参数
    temperature NUMERIC(3,2) DEFAULT 0.7,    -- 温度 (0-1)
    max_tokens INTEGER DEFAULT 4096,         -- 最大Token
    top_p NUMERIC(3,2) DEFAULT 0.9,
    frequency_penalty NUMERIC(3,2) DEFAULT 0.0,
    presence_penalty NUMERIC(3,2) DEFAULT 0.0,
    
    -- 连接测试
    last_test_at TIMESTAMP,                  -- 上次测试时间
    test_status VARCHAR(20),                 -- success/failed/pending
    test_response_time_ms INTEGER,           -- 测试响应时间
    test_error_message TEXT,                 -- 测试错误信息
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 唯一约束：每个专家只能有一个激活的API配置
    CONSTRAINT unique_active_api_per_expert 
        UNIQUE (expert_id, is_active) 
        WHERE is_active = TRUE
);

-- 索引
CREATE INDEX idx_api_config_expert ON ai_expert_api_configs(expert_id);
CREATE INDEX idx_api_config_provider ON ai_expert_api_configs(provider);
```

#### 3. `ai_expert_usage_stats` - 使用统计表
```sql
CREATE TABLE ai_expert_usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expert_id UUID NOT NULL REFERENCES ai_expert_profiles(id) ON DELETE CASCADE,
    
    -- 统计维度
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- 调用统计
    total_calls INTEGER DEFAULT 0,           -- 总调用次数
    successful_calls INTEGER DEFAULT 0,      -- 成功次数
    failed_calls INTEGER DEFAULT 0,          -- 失败次数
    
    -- Token统计
    total_input_tokens BIGINT DEFAULT 0,     -- 输入Token
    total_output_tokens BIGINT DEFAULT 0,    -- 输出Token
    total_cost_usd NUMERIC(10,4) DEFAULT 0,  -- 总成本（美元）
    
    -- 性能统计
    avg_response_time_ms INTEGER,            -- 平均响应时间
    p95_response_time_ms INTEGER,            -- P95响应时间
    p99_response_time_ms INTEGER,            -- P99响应时间
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 唯一约束
    CONSTRAINT unique_expert_date UNIQUE (expert_id, date)
);

-- 索引
CREATE INDEX idx_usage_expert_date ON ai_expert_usage_stats(expert_id, date DESC);
```

---

## 🚀 API端点设计

### RESTful API

```yaml
# 1. 获取所有专家列表
GET /api/v1/ai-experts
Response:
  {
    "builtin_experts": [
      {
        "id": "uuid",
        "name": "销售经理",
        "department": "Sales",
        "is_enabled": true,
        "api_status": "connected",
        "usage_today": {
          "calls": 45,
          "tokens": 12500,
          "cost_usd": 0.38
        }
      }
    ],
    "custom_experts": [...],
    "total_count": 12,
    "max_capacity": 32,
    "available_slots": 20
  }

# 2. 添加新专家 ⭐
POST /api/v1/ai-experts
Request:
  {
    "name": "SEO优化专家",
    "department": "Marketing",
    "specialization": "SEO, 内容优化, 关键词研究",
    "description": "专业的SEO优化专家",
    "capabilities": ["keyword_research", "content_optimization"],
    "system_prompt": "你是一个SEO专家...",
    "api_config": {
      "provider": "GPT-4",
      "api_endpoint": "https://api.openai.com/v1/chat/completions",  # ⭐ 用户填写
      "api_key": "sk-xxx...",                                         # ⭐ 用户填写
      "model_name": "gpt-4-turbo",
      "temperature": 0.7,
      "max_tokens": 4096
    }
  }
Response:
  {
    "id": "new-uuid",
    "status": "created",
    "test_result": {
      "status": "success",
      "response_time_ms": 850,
      "message": "API连接测试成功"
    }
  }

# 3. 更新专家配置
PUT /api/v1/ai-experts/{expert_id}
Request:
  {
    "name": "高级SEO专家",
    "api_config": {
      "api_endpoint": "https://new-endpoint.com/v1/chat",  # ⭐ 修改API端点
      "api_key": "new-key",
      "temperature": 0.8
    }
  }

# 4. 测试API连接 ⭐
POST /api/v1/ai-experts/{expert_id}/test-connection
Response:
  {
    "status": "success",
    "response_time_ms": 650,
    "model_info": {
      "provider": "GPT-4",
      "model": "gpt-4-turbo",
      "context_length": 128000
    },
    "sample_response": "测试消息：连接成功！"
  }

# 5. 启用/禁用专家
PATCH /api/v1/ai-experts/{expert_id}/toggle
Request:
  {
    "is_enabled": false
  }

# 6. 删除专家（仅自定义专家）
DELETE /api/v1/ai-experts/{expert_id}
Response:
  {
    "status": "deleted",
    "message": "专家 'SEO优化专家' 已删除"
  }

# 7. 获取专家使用统计
GET /api/v1/ai-experts/{expert_id}/stats?period=7d
Response:
  {
    "expert_id": "uuid",
    "period": "7d",
    "total_calls": 320,
    "success_rate": 98.5,
    "avg_response_time_ms": 780,
    "total_cost_usd": 4.56,
    "daily_breakdown": [...]
  }
```

---

## 🖥️ 前端UI组件设计

### 1. 专家管理主页 (`/ceo-dashboard/ai-experts/manage`)

```typescript
// ExpertManagementPage.tsx

interface ExpertCard {
  id: string;
  name: string;
  department: string;
  isBuiltin: boolean;
  isEnabled: boolean;
  apiStatus: 'connected' | 'disconnected' | 'error';
  usageToday: {
    calls: number;
    tokens: number;
    costUsd: number;
  };
}

const ExpertManagementPage = () => {
  return (
    <div className="expert-management">
      {/* 头部统计 */}
      <div className="stats-header">
        <StatCard label="激活专家" value={12} max={32} />
        <StatCard label="今日调用" value={456} />
        <StatCard label="今日成本" value="$12.34" />
      </div>

      {/* 添加按钮 */}
      <Button onClick={() => navigate('/add-new')}>
        ➕ 添加新专家 (剩余 20 个名额)
      </Button>

      {/* 预设专家列表 */}
      <Section title="核心专家（10个预设）">
        <ExpertGrid experts={builtinExperts} />
      </Section>

      {/* 自定义专家列表 */}
      <Section title="自定义专家（2个）">
        <ExpertGrid experts={customExperts} canDelete />
      </Section>
    </div>
  );
};
```

---

### 2. 添加专家页面 ⭐ (`/ceo-dashboard/ai-experts/add-new`)

```typescript
// AddExpertPage.tsx

const AddExpertPage = () => {
  const [formData, setFormData] = useState({
    // 基本信息
    name: '',
    department: '',
    specialization: '',
    description: '',
    
    // API配置 ⭐
    provider: 'GPT-4',
    apiEndpoint: '',      // 用户填写 ⭐
    apiKey: '',           // 用户填写 ⭐
    modelName: '',
    temperature: 0.7,
    maxTokens: 4096,
    
    // 能力定义
    capabilities: [],
    systemPrompt: '',
  });

  return (
    <Form onSubmit={handleSubmit}>
      {/* 第1步：基本信息 */}
      <Section title="1. 基本信息">
        <Input label="专家名称 *" name="name" />
        <Select label="部门 *" name="department" 
          options={['Sales', 'Marketing', 'Finance', ...]} />
        <Input label="专业领域 *" name="specialization" />
        <Textarea label="描述" name="description" />
      </Section>

      {/* 第2步：API配置 ⭐ */}
      <Section title="2. API配置">
        <Select label="LLM供应商 *" name="provider"
          options={[
            { value: 'GPT-4', label: 'OpenAI GPT-4' },
            { value: 'Claude', label: 'Anthropic Claude' },
            { value: 'DeepSeek', label: 'DeepSeek V3' },
            { value: 'Gemini', label: 'Google Gemini' },
            { value: 'Kimi', label: 'Moonshot Kimi' },
            { value: 'Grok', label: 'xAI Grok' },
            { value: 'Custom', label: '自定义端点' },
          ]} 
        />
        
        <Input 
          label="API端点URL *" 
          name="apiEndpoint"
          placeholder="https://api.openai.com/v1/chat/completions"
          helpText="⭐ 用户可以填写自己的API端点"
        />
        
        <PasswordInput 
          label="API Key *" 
          name="apiKey"
          placeholder="sk-..."
          helpText="⭐ 数据会加密存储，不会泄露"
        />
        
        <Input label="模型名称 *" name="modelName"
          placeholder="gpt-4-turbo" />
        
        <Slider label="温度参数" name="temperature"
          min={0} max={1} step={0.1} />
        
        <Input label="最大Token数" name="maxTokens" type="number" />
        
        {/* 测试连接按钮 ⭐ */}
        <Button 
          variant="outline" 
          onClick={testApiConnection}
          loading={isTesting}
        >
          🔌 测试API连接
        </Button>
        
        {testResult && (
          <Alert 
            type={testResult.status === 'success' ? 'success' : 'error'}
            message={testResult.message}
            details={`响应时间: ${testResult.response_time_ms}ms`}
          />
        )}
      </Section>

      {/* 第3步：能力定义 */}
      <Section title="3. 能力定义">
        <TagInput label="核心能力" name="capabilities" />
        <Textarea 
          label="系统提示词 *" 
          name="systemPrompt"
          rows={10}
          placeholder="你是一个专业的..."
        />
      </Section>

      {/* 提交按钮 */}
      <Button type="submit" disabled={!isValid}>
        ✅ 创建专家
      </Button>
    </Form>
  );
};
```

---

## 🔐 安全性设计

### API Key加密存储

```python
# src/security/encryption.py

from cryptography.fernet import Fernet
import os

class APIKeyEncryption:
    """API Key加密工具"""
    
    def __init__(self):
        # 从环境变量加载加密密钥
        self.key = os.getenv('ENCRYPTION_KEY').encode()
        self.cipher = Fernet(self.key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """加密API Key"""
        encrypted = self.cipher.encrypt(api_key.encode())
        return encrypted.decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """解密API Key"""
        decrypted = self.cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()

# 使用示例
encryption = APIKeyEncryption()

# 保存时加密
encrypted_key = encryption.encrypt_api_key("sk-abc123...")
# 存入数据库: api_key_encrypted = encrypted_key

# 使用时解密
original_key = encryption.decrypt_api_key(encrypted_key)
# 调用API: headers = {"Authorization": f"Bearer {original_key}"}
```

---

## 📊 使用流程示例

### 场景1: 添加一个SEO专家

```yaml
Step 1: 用户进入 /ceo-dashboard/ai-experts/add-new

Step 2: 填写基本信息
  - 名称: "SEO优化专家"
  - 部门: "Marketing"
  - 专业: "SEO, 内容优化, 关键词研究"

Step 3: 配置API ⭐
  - 选择供应商: "OpenAI GPT-4"
  - API端点: "https://api.openai.com/v1/chat/completions"  # 用户填写
  - API Key: "sk-proj-xyz..."                              # 用户填写
  - 模型: "gpt-4-turbo"
  - 温度: 0.7

Step 4: 点击"测试API连接" ⭐
  - 系统发送测试请求
  - 显示结果: ✅ 连接成功，响应时间 650ms

Step 5: 填写能力定义
  - 核心能力: ["keyword_research", "content_optimization"]
  - 系统提示词: "你是一个专业的SEO优化专家..."

Step 6: 提交创建
  - 系统验证数据
  - 加密API Key
  - 保存到数据库
  - 专家立即可用 ✅
```

---

### 场景2: CEO调用AI专家

```yaml
用户操作:
  - CEO在Dashboard输入: "帮我分析供应商XYZ的风险"

系统处理:
  1. 意图识别: 风险评估任务
  2. 专家匹配: "风险管理专家"
  3. 任务路由: 分配给风险管理专家
  4. API调用:
     - 从数据库获取专家API配置
     - 解密API Key
     - 构造请求: 
       {
         "model": "gpt-4-turbo",
         "messages": [...],
         "temperature": 0.7
       }
     - 发送到用户配置的API端点 ⭐
  5. 响应处理:
     - 记录Token使用量
     - 计算成本
     - 更新统计数据
  6. 返回结果给CEO

结果展示:
  - "风险管理专家" 的分析报告
  - Token使用: 2,340 输入 + 1,560 输出
  - 成本: $0.12
  - 响应时间: 3.2秒
```

---

## 🎯 实施计划（Week 12-13）

### Week 12: 核心开发（5天）

**Day 1-2: 数据库 + 后端API**
```yaml
- 创建3个数据表
- 实现API Key加密工具
- 开发8个RESTful API端点
- 单元测试（70个用例）
```

**Day 3-4: 前端UI**
```yaml
- 专家管理主页
- 添加专家表单（含API配置）⭐
- 编辑专家页面
- 测试连接功能 ⭐
```

**Day 5: 预设数据 + 集成测试**
```yaml
- 初始化10个核心专家
- 配置默认API端点
- 端到端测试
- 性能优化
```

---

### Week 13: 优化 + 监控（5天）

**Day 1-2: 使用统计 + 监控**
```yaml
- 实时Token统计
- 成本计算
- 性能监控Dashboard
```

**Day 3-4: 高级功能**
```yaml
- 专家协作引擎
- 智能任务路由
- 负载均衡
```

**Day 5: 文档 + 演示**
```yaml
- API文档
- 用户指南
- 演示视频
```

---

## ✅ 验收标准

### 功能验收

**核心功能**:
- ✅ 10个预设专家可用
- ✅ 用户可以添加新专家（最多32个）
- ✅ 每个专家可以配置自己的API端点 ⭐
- ✅ 每个专家可以配置自己的API Key ⭐
- ✅ 支持6种LLM供应商（GPT-4, Claude, DeepSeek, Gemini, Kimi, Grok）
- ✅ API连接测试功能正常 ⭐
- ✅ API Key加密存储
- ✅ 启用/禁用专家
- ✅ 删除自定义专家
- ✅ 使用统计和成本跟踪

**性能要求**:
- 添加专家响应时间 < 1秒
- API测试连接 < 3秒
- 专家列表加载 < 500ms
- 支持32个专家并发调用

---

## 🚀 总结

这个设计完全满足你的需求：

1. ✅ **10个核心专家**（预设，涵盖常用场景）
2. ✅ **可扩展到32个**（通过UI添加）
3. ✅ **可配置API端点** ⭐（每个专家独立配置）
4. ✅ **API Key管理** ⭐（加密存储，安全可靠）
5. ✅ **测试连接功能** ⭐（确保API可用）
6. ✅ **使用统计**（Token、成本、性能监控）

**核心优势**:
- 🎯 满足你的所有明确要求
- 🔒 安全可靠（API Key加密）
- 🚀 易于扩展（模块化设计）
- 📊 完整监控（使用统计、成本追踪）
- 🎨 友好界面（直观的UI操作）

这个系统在 **Week 12-13（10天）** 就可以完整实现！
