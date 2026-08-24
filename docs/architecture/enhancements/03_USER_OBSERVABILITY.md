# Enhancement Point 3: User-Facing Observability & Debugging

## 问题陈述

**当前状态：** 有监控系统，但用户侧的"透明度"不足

**核心问题：**
```
用户视角的困惑：
├─ 鎏灏为什么做这个决策？
├─ 鎏灏的推理过程是什么？
├─ 为什么这个任务失败了？
├─ AI调用了哪些模型？花了多少钱？
├─ 我能看到完整的执行日志吗？
├─ 如何调试AI的错误输出？
└─ 如何验证AI的推理是否合理？
```

---

## 完整解决方案

### 1. Decision Transparency（决策透明）

#### 1.1 AI推理可视化

```yaml
推理过程展示:

基础信息:
├─ 任务ID
├─ 开始时间 / 结束时间
├─ 总耗时
├─ 最终状态（成功/失败/超时）
└─ 执行者（哪个Agent/Model）

推理步骤:
Step 1: 理解需求
├─ 用户输入: "分析这个月的销售情况"
├─ 理解结果:
│   ├─ 意图: 销售数据分析
│   ├─ 时间范围: 本月（2026-08-01 到 2026-08-22）
│   ├─ 需要的数据: 订单、客户、产品
│   └─ 输出格式: 分析报告
└─ 置信度: 95%

Step 2: 数据收集
├─ 查询数据库
│   ├─ 查询1: SELECT * FROM orders WHERE created_at >= '2026-08-01'
│   ├─ 结果: 156条订单
│   ├─ 耗时: 45ms
│   └─ 状态: 成功
├─ 查询2: SELECT * FROM customers WHERE last_order_date >= '2026-08-01'
│   ├─ 结果: 89个客户
│   ├─ 耗时: 32ms
│   └─ 状态: 成功
└─ 数据准备完成

Step 3: AI分析
├─ 调用模型: GPT-4
├─ Prompt:
│   ```
│   Analyze the following sales data:
│   - Total Orders: 156
│   - Total Revenue: $245,680
│   - Unique Customers: 89
│   - Average Order Value: $1,575
│   ...
│   ```
├─ Token使用:
│   ├─ Input: 1,234 tokens
│   ├─ Output: 567 tokens
│   └─ Cost: $0.0234
├─ 耗时: 3.2s
└─ 状态: 成功

Step 4: 结果生成
├─ 提取关键洞察
│   ├─ 销售额同比增长 15%
│   ├─ 新客户占比 32%
│   ├─ 复购率 68%
│   └─ Top 3产品: A, B, C
├─ 生成可视化图表
│   ├─ 销售趋势图
│   ├─ 产品分布图
│   └─ 客户分析图
└─ 格式化输出

最终输出:
├─ 文字报告
├─ 图表
├─ 可执行建议
│   ├─ 建议1: 加大对产品A的推广
│   ├─ 建议2: 针对新客户设计转化策略
│   └─ 建议3: 提升复购率的营销活动
└─ 置信度: 85%

数据依据:
├─ 156条订单数据
├─ 89个客户数据
├─ 历史3个月对比数据
└─ 行业基准数据
```

#### 1.2 实现代码

```python
# liuhao/core/observability/decision_tracker.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ReasoningStep:
    """推理步骤"""
    step_number: int
    step_name: str
    description: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    # 输入输出
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 执行细节
    sub_steps: List['ReasoningStep'] = field(default_factory=list)
    queries: List[Dict] = field(default_factory=list)
    ai_calls: List[Dict] = field(default_factory=list)
    
    # 元数据
    confidence: float = 1.0
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

@dataclass
class DecisionTrace:
    """决策追踪"""
    trace_id: str
    task_id: str
    user_id: str
    tenant_id: str
    
    # 基本信息
    user_input: str
    final_output: Any
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    status: str = "running"
    
    # 推理过程
    steps: List[ReasoningStep] = field(default_factory=list)
    
    # 资源使用
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    models_used: List[str] = field(default_factory=list)
    
    # 数据来源
    data_sources: List[str] = field(default_factory=list)
    
    def to_user_friendly_format(self) -> Dict:
        """转换为用户友好的格式"""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "duration": f"{self.total_duration_ms}ms" if self.total_duration_ms else "N/A",
            "cost": f"${self.total_cost_usd:.4f}",
            "reasoning_process": [
                {
                    "step": step.step_number,
                    "name": step.step_name,
                    "description": step.description,
                    "status": step.status.value,
                    "duration": f"{step.duration_ms}ms" if step.duration_ms else "N/A",
                    "details": {
                        "inputs": step.inputs,
                        "outputs": step.outputs,
                        "queries": len(step.queries),
                        "ai_calls": len(step.ai_calls),
                    },
                    "confidence": f"{step.confidence * 100:.1f}%",
                }
                for step in self.steps
            ],
            "models_used": self.models_used,
            "data_sources": self.data_sources,
        }

class DecisionTracker:
    """决策追踪器"""
    
    def __init__(self):
        self.active_traces: Dict[str, DecisionTrace] = {}
    
    def start_trace(self, trace_id: str, task_id: str, user_input: str, user_id: str, tenant_id: str):
        """开始追踪"""
        trace = DecisionTrace(
            trace_id=trace_id,
            task_id=task_id,
            user_id=user_id,
            tenant_id=tenant_id,
            user_input=user_input,
            final_output=None,
            start_time=datetime.now()
        )
        self.active_traces[trace_id] = trace
        return trace
    
    def add_step(self, trace_id: str, step: ReasoningStep):
        """添加推理步骤"""
        if trace_id in self.active_traces:
            self.active_traces[trace_id].steps.append(step)
    
    def record_ai_call(self, trace_id: str, model: str, tokens: int, cost: float):
        """记录AI调用"""
        if trace_id in self.active_traces:
            trace = self.active_traces[trace_id]
            trace.total_tokens += tokens
            trace.total_cost_usd += cost
            if model not in trace.models_used:
                trace.models_used.append(model)
    
    def end_trace(self, trace_id: str, final_output: Any, status: str):
        """结束追踪"""
        if trace_id in self.active_traces:
            trace = self.active_traces[trace_id]
            trace.end_time = datetime.now()
            trace.total_duration_ms = int((trace.end_time - trace.start_time).total_seconds() * 1000)
            trace.final_output = final_output
            trace.status = status
            
            # 保存到数据库
            self._save_to_database(trace)
            
            # 从活跃列表移除
            del self.active_traces[trace_id]
    
    def get_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """获取追踪"""
        if trace_id in self.active_traces:
            return self.active_traces[trace_id]
        return self._load_from_database(trace_id)
```

---

### 2. Execution Trace（执行追踪）

#### 2.1 任务执行时间线

```yaml
时间线视图:

Timeline: Task #12345 "Generate Sales Report"
├─ 00:00.000 - Task Created
│   ├─ User: zhang@example.com
│   ├─ Priority: High
│   └─ Assigned to: AI Agent (Sales)
│
├─ 00:00.050 - Task Started
│   ├─ Agent: Sales AI Agent
│   ├─ Initial Assessment
│   └─ Breaking down into subtasks
│
├─ 00:00.200 - Subtask 1: Data Collection
│   ├─ Query Database
│   │   ├─ Query 1: Orders (45ms) ✓
│   │   ├─ Query 2: Customers (32ms) ✓
│   │   └─ Query 3: Products (28ms) ✓
│   └─ Total: 105ms
│
├─ 00:00.305 - Subtask 2: Data Processing
│   ├─ Calculate Metrics
│   │   ├─ Total Revenue ✓
│   │   ├─ Average Order Value ✓
│   │   └─ Customer Segments ✓
│   └─ Total: 42ms
│
├─ 00:00.347 - Subtask 3: AI Analysis
│   ├─ Call GPT-4
│   │   ├─ Prompt Engineering (15ms)
│   │   ├─ API Call (3,200ms) ✓
│   │   └─ Response Parsing (8ms)
│   ├─ Tokens: 1,234 input + 567 output
│   ├─ Cost: $0.0234
│   └─ Total: 3,223ms
│
├─ 00:03.570 - Subtask 4: Generate Visualizations
│   ├─ Chart 1: Sales Trend (120ms) ✓
│   ├─ Chart 2: Product Distribution (95ms) ✓
│   └─ Chart 3: Customer Segments (88ms) ✓
│   └─ Total: 303ms
│
├─ 00:03.873 - Subtask 5: Format Output
│   ├─ Generate PDF (456ms) ✓
│   ├─ Upload to Storage (234ms) ✓
│   └─ Total: 690ms
│
└─ 00:04.563 - Task Completed ✓
    ├─ Total Duration: 4,563ms
    ├─ Success Rate: 100%
    └─ Output: sales_report_2026_08.pdf

Performance Breakdown:
├─ Data Collection: 105ms (2.3%)
├─ Data Processing: 42ms (0.9%)
├─ AI Analysis: 3,223ms (70.6%) ← Bottleneck
├─ Visualization: 303ms (6.6%)
├─ Output Generation: 690ms (15.1%)
└─ Overhead: 200ms (4.4%)

Recommendations:
├─ AI Analysis is the bottleneck
├─ Consider caching similar queries
└─ Estimated savings: 2s per similar request
```

#### 2.2 多Agent协同追踪

```yaml
Multi-Agent Task: "Launch Product in Germany Market"

Orchestrator: LiuHao Main Brain
├─ Task Received: "Launch Product X in Germany"
├─ Strategy:
│   ├─ Parallel Execution
│   ├─ 5 Agents assigned
│   └─ Estimated: 2 hours
│
├─ [00:00] Dispatch to Agents
│   ├─ → Market Research Agent
│   ├─ → Legal Agent
│   ├─ → Marketing Agent
│   ├─ → Product Agent
│   └─ → Logistics Agent
│
├─ [00:05] Market Research Agent - Started
│   ├─ Task: Analyze Germany Market
│   ├─ Status: Researching competitors
│   └─ Progress: 20%
│
├─ [00:05] Legal Agent - Started
│   ├─ Task: Check German regulations
│   ├─ Status: Reading legal documents
│   └─ Progress: 15%
│
├─ [00:05] Marketing Agent - Started
│   ├─ Task: Design marketing campaign
│   ├─ Status: Analyzing target audience
│   └─ Progress: 10%
│
├─ [00:15] Market Research Agent - Completed ✓
│   ├─ Output: Market Analysis Report
│   ├─ Key Findings:
│   │   ├─ Market Size: €500M
│   │   ├─ Main Competitors: 3
│   │   └─ Opportunity Score: 8/10
│   └─ Confidence: 85%
│
├─ [00:18] Orchestrator - Dependency Resolved
│   ├─ Market Research done
│   ├─ Unblock: Marketing Agent (needs market data)
│   └─ Unblock: Product Agent (needs competitor info)
│
├─ [00:20] Legal Agent - Completed ✓
│   ├─ Output: Legal Compliance Report
│   ├─ Key Findings:
│   │   ├─ Required Certifications: CE, TÜV
│   │   ├─ Import Taxes: 15%
│   │   └─ Timeline: 3 months
│   └─ Status: All Clear ✓
│
├─ [00:25] Product Agent - Progress Update
│   ├─ Task: Adapt product for Germany
│   ├─ Status: Adjusting specifications
│   ├─ Changes:
│   │   ├─ Voltage: 230V (done)
│   │   ├─ Language: German manual (in progress)
│   │   └─ Compliance: CE marking (pending)
│   └─ Progress: 60%
│
├─ [00:30] Marketing Agent - Completed ✓
│   ├─ Output: Marketing Campaign Plan
│   ├─ Budget: €50,000
│   ├─ Channels: Online + Trade Shows
│   └─ Expected ROI: 3.5x
│
├─ [00:45] Product Agent - Completed ✓
│   ├─ Output: Product Adaptation Plan
│   ├─ Timeline: 6 weeks
│   └─ Cost: €30,000
│
├─ [00:50] Logistics Agent - Completed ✓
│   ├─ Output: Logistics & Distribution Plan
│   ├─ Warehouse: Hamburg
│   ├─ Shipping Partner: DHL
│   └─ First Shipment: 4 weeks
│
└─ [01:00] Orchestrator - Final Report
    ├─ All Agents Completed ✓
    ├─ Synthesizing Results...
    ├─ Final Recommendation:
    │   ├─ Go/No-Go: GO ✓
    │   ├─ Timeline: 3 months
    │   ├─ Total Investment: €80,000
    │   ├─ Expected Revenue: €500,000 (Year 1)
    │   └─ ROI: 6.25x
    └─ Next Steps: [Review, Approve, Execute]

Agent Performance:
├─ Market Research Agent: 15min ✓ On-time
├─ Legal Agent: 20min ✓ On-time
├─ Marketing Agent: 30min ✓ On-time
├─ Product Agent: 45min ✓ On-time
├─ Logistics Agent: 50min ✓ On-time
└─ Total: 1hour (vs estimated 2hours) - 50% faster!
```

---

### 3. Cost Tracking（成本追踪）

#### 3.1 实时成本监控

```yaml
成本Dashboard:

今日使用情况:
├─ AI Token使用
│   ├─ Total: 1,234,567 tokens
│   ├─ GPT-4: 456,789 tokens ($13.70)
│   ├─ Claude: 345,678 tokens ($8.64)
│   ├─ DeepSeek: 432,100 tokens ($0.43)
│   └─ Total Cost: $22.77
│
├─ 按任务类型分类
│   ├─ Sales Tasks: $8.50 (37%)
│   ├─ Marketing Tasks: $6.20 (27%)
│   ├─ Research Tasks: $4.80 (21%)
│   ├─ Customer Service: $2.50 (11%)
│   └─ Other: $0.77 (4%)
│
├─ 按用户分类 (Top 5)
│   ├─ zhang@example.com: $5.60
│   ├─ li@example.com: $4.20
│   ├─ wang@example.com: $3.80
│   ├─ chen@example.com: $2.90
│   └─ others: $6.27
│
└─ 成本趋势
    ├─ Today: $22.77
    ├─ Yesterday: $18.50 (+23% ↑)
    ├─ This Week: $125.40
    ├─ This Month: $478.90
    └─ Projected (Month): $650 (vs Budget: $500 ⚠️)

配额管理:
├─ Current Quota
│   ├─ Monthly: $500
│   ├─ Used: $478.90 (95.8%)
│   ├─ Remaining: $21.10 (4.2%)
│   └─ Status: ⚠️ Warning (< 10% remaining)
│
├─ Rate Limiting
│   ├─ Requests/Minute: 45 / 100
│   ├─ Tokens/Hour: 12,500 / 50,000
│   └─ Daily Budget: $22.77 / $30
│
└─ Alerts
    ├─ [Warning] 95% of monthly quota used
    ├─ [Info] GPT-4 usage 30% higher than average
    └─ [Tip] Consider using DeepSeek for simple tasks

成本优化建议:
├─ Task Type Optimization
│   ├─ Simple queries: Use DeepSeek (10x cheaper)
│   ├─ Complex tasks: Use GPT-4
│   └─ Estimated Savings: $50/month
│
├─ Caching Opportunities
│   ├─ 15% queries are duplicates
│   ├─ Enable caching for common questions
│   └─ Estimated Savings: $30/month
│
└─ Off-Peak Usage
    ├─ Batch non-urgent tasks
    ├─ Run during off-peak hours
    └─ Estimated Savings: $20/month

Total Potential Savings: $100/month (20%)
```

#### 3.2 成本归因分析

```python
# liuhao/core/billing/cost_tracker.py

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from enum import Enum

class CostCategory(Enum):
    """成本类别"""
    AI_TOKENS = "ai_tokens"
    STORAGE = "storage"
    API_CALLS = "api_calls"
    BANDWIDTH = "bandwidth"

@dataclass
class CostEntry:
    """成本记录"""
    entry_id: str
    tenant_id: str
    user_id: str
    task_id: str
    timestamp: datetime
    category: CostCategory
    
    # 资源使用
    resource_type: str  # gpt-4, claude, etc.
    quantity: float      # tokens, bytes, etc.
    unit_price: float
    total_cost: float
    
    # 归因
    department_id: Optional[str] = None
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

class CostTracker:
    """成本追踪器"""
    
    def __init__(self):
        self.cost_entries: List[CostEntry] = []
    
    def record_cost(self, entry: CostEntry):
        """记录成本"""
        # 1. 保存到时序数据库
        self._save_to_timeseries_db(entry)
        
        # 2. 更新实时统计
        self._update_realtime_stats(entry)
        
        # 3. 检查配额
        if self._check_quota_exceeded(entry.tenant_id):
            self._send_quota_alert(entry.tenant_id)
        
        # 4. 触发成本优化建议
        if self._should_suggest_optimization(entry):
            self._generate_optimization_suggestions(entry.tenant_id)
    
    def get_cost_breakdown(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """获取成本分解"""
        query = f"""
        SELECT 
            category,
            resource_type,
            SUM(total_cost) as cost,
            SUM(quantity) as quantity
        FROM cost_entries
        WHERE tenant_id = '{tenant_id}'
          AND timestamp BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY category, resource_type
        ORDER BY cost DESC
        """
        
        results = self._query_database(query)
        
        return {
            "total_cost": sum(r["cost"] for r in results),
            "breakdown_by_category": self._group_by(results, "category"),
            "breakdown_by_resource": self._group_by(results, "resource_type"),
            "top_users": self._get_top_users_by_cost(tenant_id, start_date, end_date),
            "optimization_opportunities": self._identify_optimization_opportunities(results)
        }
    
    def _identify_optimization_opportunities(self, results: List[Dict]) -> List[Dict]:
        """识别优化机会"""
        opportunities = []
        
        # 1. 检查是否大量使用昂贵模型
        gpt4_cost = sum(r["cost"] for r in results if r["resource_type"] == "gpt-4")
        total_cost = sum(r["cost"] for r in results)
        
        if gpt4_cost / total_cost > 0.7:  # GPT-4占比超过70%
            opportunities.append({
                "type": "model_optimization",
                "description": "Consider using cheaper models for simple tasks",
                "potential_savings": gpt4_cost * 0.3,  # 假设能节省30%
                "action": "Use DeepSeek or Claude for non-complex tasks"
            })
        
        # 2. 检查重复查询
        # ...
        
        return opportunities
```

---

### 4. Debug Mode（调试模式）

#### 4.1 开发者工具

```yaml
开发者模式功能:

Complete Request/Response Log:
├─ HTTP Request
│   ├─ Method: POST
│   ├─ URL: /api/ai/ask
│   ├─ Headers:
│   │   ├─ Authorization: Bearer xxx
│   │   ├─ Content-Type: application/json
│   │   └─ X-Request-ID: req-12345
│   └─ Body:
│       {
│         "question": "分析销售情况",
│         "context": {...}
│       }
│
├─ Internal Processing
│   ├─ Step 1: Authentication (5ms)
│   ├─ Step 2: Rate Limiting (2ms)
│   ├─ Step 3: Input Validation (3ms)
│   ├─ Step 4: Intent Recognition (120ms)
│   │   ├─ AI Model: GPT-4
│   │   ├─ Prompt: [显示完整Prompt]
│   │   └─ Response: [显示完整Response]
│   ├─ Step 5: Task Execution (3,500ms)
│   │   ├─ Database Queries: [3 queries, 显示SQL]
│   │   ├─ AI Analysis: [显示完整交互]
│   │   └─ Result Generation: [显示中间结果]
│   └─ Step 6: Response Formatting (50ms)
│
└─ HTTP Response
    ├─ Status: 200 OK
    ├─ Headers:
    │   ├─ X-Request-ID: req-12345
    │   ├─ X-Processing-Time: 3,680ms
    │   └─ X-Cost: $0.0234
    └─ Body: [完整响应]

Replay功能:
├─ 保存完整上下文
├─ 可以重放任意请求
├─ 修改输入测试不同场景
└─ 对比不同模型的输出

AI Prompt Inspection:
├─ 查看完整Prompt
│   ```
│   System: You are a sales analyst AI...
│   
│   User: Analyze the following data:
│   Orders: 156
│   Revenue: $245,680
│   ...
│   ```
├─ 查看Prompt Engineering策略
│   ├─ Few-shot examples used: 3
│   ├─ Chain-of-Thought: Enabled
│   └─ Temperature: 0.7
└─ 查看原始AI响应
    ```json
    {
      "analysis": "...",
      "confidence": 0.85,
      "reasoning": "..."
    }
    ```

Performance Profiling:
├─ 时间分解
│   ├─ Network: 50ms
│   ├─ Auth: 5ms
│   ├─ Business Logic: 3,500ms
│   ├─ AI Calls: 3,200ms (91%)
│   └─ Database: 100ms (3%)
├─ 瓶颈识别
│   └─ AI Calls是主要瓶颈
└─ 优化建议
    ├─ 考虑缓存相似查询
    └─ 使用更快的模型处理简单任务
```

---

## 总结

**用户侧可观测性的核心要点：**

1. **决策透明**：用户能看懂AI的推理过程
2. **执行追踪**：完整的任务执行时间线
3. **成本透明**：实时成本追踪和优化建议
4. **调试工具**：开发者模式，完整的请求/响应日志
5. **性能洞察**：识别瓶颈，提供优化建议

**实施优先级：**
- P0: 基本执行日志、成本追踪
- P1: 决策透明、时间线视图
- P2: 调试模式、性能分析
- P3: 高级分析、优化建议

---

## 下一步

完善点4：[AI模型演进策略](./04_AI_MODEL_EVOLUTION.md)
