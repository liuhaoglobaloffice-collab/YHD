# Week 2 Day 4 开发任务

**日期**: 2026-08-24  
**负责人**: 开发工程师  
**预计时间**: 8 小时

---

## 任务 1: 实现风险评估 AI Agent (2 小时)

### 目标
创建 `SupplierRiskAgent`，使用 AI 分析供应商风险等级。

### 文件位置
`src/business/supplier/risk_agent.py`

### 功能需求

1. **输入**:
   - 供应商基本信息 (公司名称、国家、行业)
   - 联系人信息
   - 证书信息
   - 历史风险评估记录

2. **输出**:
   - 综合风险评分 (0-100)
   - 风险等级 (LOW/MEDIUM/HIGH/CRITICAL)
   - 各维度评分:
     - 合规评分 (compliance_score)
     - 财务评分 (financial_score)
     - 履约评分 (delivery_score)
     - 质量评分 (quality_score)
     - 沟通评分 (communication_score)
   - 优势、劣势、机会、威胁 (SWOT)

3. **AI 逻辑**:
   - 调用 GPT-4o 或 Claude 分析
   - Prompt 包含供应商完整信息
   - 结构化输出 (JSON)

### 实现步骤

```python
# 1. 创建 risk_agent.py
from src.ai.agent import BaseAgent
from src.business.supplier.crud import SupplierCRUD
from src.business.supplier.models import RiskLevel

class SupplierRiskAgent(BaseAgent):
    async def assess_risk(self, supplier_id: int) -> dict:
        # 1. 获取供应商完整信息
        # 2. 构建 AI Prompt
        # 3. 调用 AI 分析
        # 4. 解析 JSON 结果
        # 5. 保存到 supplier_risk_assessments 表
        pass
```

### 验收标准
- ✅ 能成功分析供应商风险
- ✅ 返回结构化评分数据
- ✅ 保存到数据库
- ✅ 单元测试通过 (3 个测试用例)

---

## 任务 2: 实现 Dashboard API (2 小时)

### 目标
创建 CEO Dashboard 所需的统计 API。

### 文件位置
`src/api/routes/dashboard.py` (新建)

### API 端点

#### 2.1 供应商统计
```yaml
端点: GET /api/v1/dashboard/supplier-stats
功能: 返回供应商概览统计
响应:
  total_suppliers: 总供应商数
  active_suppliers: 活跃供应商
  blacklisted_suppliers: 黑名单供应商
  by_country: 按国家统计 (Top 5)
  by_risk_level: 按风险等级统计
  recent_added: 最近添加 (7 天内)
```

#### 2.2 风险概览
```yaml
端点: GET /api/v1/dashboard/risk-overview
功能: 返回风险评估概览
响应:
  high_risk_count: 高风险供应商数
  medium_risk_count: 中风险供应商数
  low_risk_count: 低风险供应商数
  average_score: 平均风险评分
  trend: 风险趋势 (上升/下降)
```

#### 2.3 最近数据采集
```yaml
端点: GET /api/v1/dashboard/recent-collections
功能: 返回最近的数据采集记录
参数: limit (默认 10)
响应:
  - supplier_name
  - collected_at
  - data_quality_score
  - fields_collected
```

### 实现步骤

```python
# 1. 创建 dashboard.py
from fastapi import APIRouter, Depends
from src.api.dependencies.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/supplier-stats")
async def get_supplier_stats(db: AsyncSession = Depends(get_db)):
    # 实现统计逻辑
    pass

@router.get("/risk-overview")
async def get_risk_overview(db: AsyncSession = Depends(get_db)):
    # 实现风险概览
    pass

@router.get("/recent-collections")
async def get_recent_collections(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    # 实现采集记录查询
    pass
```

### 验收标准
- ✅ 3 个 API 端点正常工作
- ✅ 返回正确的统计数据
- ✅ API 测试通过 (10 个测试用例)

---

## 任务 3: Knowledge 集成完善 (2 小时)

### 目标
完成 `_get_embedding()` 方法，支持文本向量化。

### 文件位置
`src/knowledge/core.py`

### 实现方案

#### 方案 A: 使用 OpenAI Embeddings (推荐)
```python
async def _get_embedding(self, text: str) -> List[float]:
    """生成文本向量"""
    response = await self.openai_client.embeddings.create(
        model="text-embedding-3-small",  # 1536 维
        input=text
    )
    return response.data[0].embedding
```

#### 方案 B: 使用本地模型 (Week 4 集成)
```python
# 暂时返回模拟向量，Week 4 替换为 Ollama
async def _get_embedding(self, text: str) -> List[float]:
    # TODO: Week 4 集成 Ollama + Qwen2.5
    return [0.0] * 1536  # 占位符
```

### 验收标准
- ✅ 方法正常工作
- ✅ 返回正确维度的向量
- ✅ 单元测试通过 (5 个测试用例)

---

## 任务 4: 清理 P2 问题 (2 小时)

### 4.1 修复 3 个 Migration 测试

**问题**: 数据库迁移版本不一致

**文件**: `tests/test_migration.py`

**修复步骤**:
1. 检查当前 Alembic 版本
   ```bash
   alembic current
   ```
2. 更新测试中的预期版本号
3. 重新运行测试验证

### 4.2 统一 Business 模块组织

**目标**: 将平铺文件改为目录结构

**当前结构**:
```
business/
├── supplier/  (完整)
├── research.py
├── sales.py
├── operations.py
└── marketing.py
```

**目标结构**:
```
business/
├── supplier/  ✅
├── research/  (新建)
├── sales/     (新建)
├── operations/ (新建)
└── marketing/ (新建)
```

**操作**:
```bash
# 为每个模块创建目录
mkdir src/business/research
mkdir src/business/sales
mkdir src/business/operations
mkdir src/business/marketing

# 移动文件并创建 __init__.py
mv src/business/research.py src/business/research/service.py
# ... (其他模块同理)
```

### 验收标准
- ✅ 3 个 Migration 测试通过
- ✅ Business 模块结构统一
- ✅ 全量测试通过率保持 > 98%

---

## 执行顺序

```bash
# 上午 (4h)
09:00 - 11:00  任务 1: 风险评估 AI Agent
11:00 - 13:00  任务 2: Dashboard API

# 下午 (4h)
14:00 - 16:00  任务 3: Knowledge 集成完善
16:00 - 18:00  任务 4: 清理 P2 问题
```

---

## 验收标准总结

### 代码质量
- ✅ 新增代码符合命名规范
- ✅ 所有方法有文档字符串
- ✅ 无 Flake8 警告

### 测试覆盖
- ✅ 新功能单元测试覆盖 > 80%
- ✅ 全量测试通过率 > 98%
- ✅ 无新增 P0/P1 Bug

### 功能完整性
- ✅ 风险评估 Agent 可用
- ✅ Dashboard API 返回正确数据
- ✅ Knowledge 向量化正常工作
- ✅ P2 问题全部修复

---

## 提交要求

完成后提交：
1. 代码变更 (Git commit)
2. 单元测试结果截图
3. API 测试结果 (Postman/curl)
4. 简短完成报告 (200 字)

---

**开始时间**: 现在  
**预计完成**: 今日 18:00  
**下一步**: Week 2 Day 5 演示数据准备
