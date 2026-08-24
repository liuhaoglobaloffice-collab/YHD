# Week 3 执行计划：API 完善与测试加固

**项目**: LiuHao AI-OS Y1.0  
**负责人**: Codex AI - 开发工程师  
**时间**: Week 3 (7天)  
**目标**: 完善 Business API + 集成测试覆盖率 > 85% + 性能优化

---

## 📊 当前状态 (Week 2 完成)

### ✅ 已完成
- Supplier CRUD 完整实现
- 5个 Supplier API 端点
- 6个 Dashboard API 端点
- 风险评估 AI 引擎
- 前端 UI 系统（CEO Dashboard + Supplier 管理）
- RBAC 权限系统
- 架构稳定性修复（循环导入、路由前缀）

### ⚠️ 当前问题
1. **测试覆盖率**: 67% (目标 85%)
2. **集成测试不足**: 缺少端到端 API 测试
3. **性能未优化**: 无性能基准测试
4. **API 文档不完整**: 部分端点缺少详细说明
5. **错误处理不统一**: 各模块异常处理不一致

### 📈 测试状态
- **总测试数**: 541 个
- **通过**: 501 个 (92.6%)
- **失败**: 8 个 (Supplier CRUD 5个 + Migration 3个)
- **跳过**: 6 个
- **错误**: 3 个 (collection errors)
- **覆盖率**: 67%

---

## 🎯 Week 3 目标

### 核心指标
- ✅ **测试覆盖率**: 67% → **85%+**
- ✅ **API 测试**: 新增 50+ 集成测试
- ✅ **性能基准**: 建立 API 响应时间基准
- ✅ **文档完整度**: 100% API 端点文档化
- ✅ **错误处理**: 统一异常处理机制

### 不做的事情（Week 3 约束）
- ❌ 不新增业务功能
- ❌ 不修改前端 UI
- ❌ 不引入新技术栈
- ❌ 不重构核心架构

---

## 📋 Week 3 任务分解

### Day 1-2: API 完善 (2天)

#### Task 1.1: 修复现有 API 问题 (P0)
**负责**: 开发工程师  
**时间**: 0.5天

**操作**:
1. 修复 Supplier CRUD 5个失败测试
   - 问题：时间戳字段精度不匹配
   - 文件：`tests/business/test_supplier_crud.py`
   - 修复：调整断言或字段映射

2. 修复 Migration 3个失败测试
   - 问题：版本断言逻辑错误
   - 文件：`tests/migrations/`
   - 修复：更新测试断言

3. 修复 3个 collection errors
   - 文件：
     - `tests/api/test_dashboard.py`
     - `tests/performance/test_api_benchmark.py`
     - `tests/performance/test_database_benchmark.py`
   - 问题：import 错误或 schema 问题

**验收标准**:
```bash
pytest tests/ -v --tb=short
# 目标: 0 failed, 0 errors
```

#### Task 1.2: 统一错误处理机制 (P1)
**负责**: 开发工程师  
**时间**: 0.5天

**创建文件**:
- `src/api/exceptions.py` - 自定义异常类
- `src/api/error_handlers.py` - 全局异常处理器

**实现功能**:
```python
# 自定义异常
class BusinessLogicError(Exception)
class ResourceNotFoundError(Exception)
class ValidationError(Exception)
class AuthorizationError(Exception)

# 全局处理器
@app.exception_handler(BusinessLogicError)
async def business_logic_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_code": "BUSINESS_ERROR"}
    )
```

**影响范围**:
- 所有 API 端点统一返回格式
- 日志记录标准化

#### Task 1.3: API 文档完善 (P2)
**负责**: 开发工程师  
**时间**: 1天

**检查清单**:
- [ ] 所有端点有 `summary` 和 `description`
- [ ] 所有请求参数有详细说明
- [ ] 所有响应模型有示例
- [ ] 错误响应码文档化（400, 401, 403, 404, 500）

**目标文件**:
- `src/api/routes/*.py` - 32个路由文件

**示例**:
```python
@router.post(
    "/suppliers",
    response_model=SupplierResponse,
    status_code=201,
    summary="创建供应商",
    description="""
    创建一个新的供应商记录。
    
    **权限要求**: ADMIN 或 SUPPLIER_CREATE
    
    **业务规则**:
    - 供应商代码必须唯一
    - 联系邮箱必须有效
    - 注册资本必须 > 0
    
    **返回**:
    - 201: 创建成功，返回完整供应商信息
    - 400: 验证失败（重复代码、无效数据）
    - 401: 未认证
    - 403: 无权限
    """,
    responses={
        400: {"description": "验证失败", "model": ErrorResponse},
        401: {"description": "未认证", "model": ErrorResponse},
        403: {"description": "无权限", "model": ErrorResponse},
    }
)
async def create_supplier(...):
    ...
```

---

### Day 3-4: 集成测试加固 (2天)

#### Task 2.1: API 集成测试套件 (P0)
**负责**: 开发工程师  
**时间**: 1.5天

**创建目录**:
```
tests/integration/
├── __init__.py
├── conftest.py          # 集成测试fixtures
├── test_supplier_api_flow.py      # 供应商完整流程
├── test_dashboard_api.py          # Dashboard API
├── test_auth_flow.py              # 认证授权流程
├── test_rbac_integration.py       # RBAC集成
├── test_audit_logging.py          # 审计日志
└── test_error_handling.py         # 错误处理
```

**测试场景**:

1. **供应商完整流程** (15个测试)
   ```python
   def test_supplier_lifecycle():
       # 1. 创建供应商
       # 2. 查询供应商
       # 3. 更新供应商
       # 4. 添加联系人
       # 5. 添加证书
       # 6. 风险评估
       # 7. 列表查询（过滤、排序、分页）
       # 8. 搜索
       # 9. 黑名单操作
       # 10. 删除
   ```

2. **Dashboard API** (10个测试)
   ```python
   def test_dashboard_stats()
   def test_dashboard_trends()
   def test_dashboard_top_suppliers()
   def test_dashboard_alerts()
   def test_dashboard_system_health()
   def test_dashboard_recent_activity()
   ```

3. **认证授权流程** (12个测试)
   ```python
   def test_login_success()
   def test_login_invalid_credentials()
   def test_access_protected_endpoint_without_token()
   def test_access_with_expired_token()
   def test_rbac_admin_can_create_supplier()
   def test_rbac_viewer_cannot_create_supplier()
   ```

4. **错误处理** (8个测试)
   ```python
   def test_400_validation_error()
   def test_401_unauthorized()
   def test_403_forbidden()
   def test_404_not_found()
   def test_500_internal_error()
   ```

**验收标准**:
- 新增集成测试 > 50 个
- 所有测试通过
- 覆盖核心业务流程

#### Task 2.2: 提升单元测试覆盖率 (P1)
**负责**: 开发工程师  
**时间**: 0.5天

**目标模块** (当前覆盖率 < 80%):
```bash
# 检查覆盖率
pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

# 重点补充测试：
- src/api/routes/dashboard.py      # 新增模块
- src/ai_brain/risk_assessment.py  # 新增模块
- src/business/supplier/crud.py    # 异常场景不足
- src/core/errors.py               # 错误处理
```

**补充测试场景**:
- 边界条件测试
- 异常场景测试
- 空值/None 测试
- 并发测试

---

### Day 5: 性能优化 (1天)

#### Task 3.1: 性能基准测试 (P1)
**负责**: 开发工程师  
**时间**: 0.5天

**创建文件**:
```
tests/performance/
├── test_api_response_time.py
├── test_database_query_performance.py
└── test_concurrent_requests.py
```

**测试内容**:

1. **API 响应时间基准**
   ```python
   @pytest.mark.benchmark
   def test_get_supplier_list_performance(benchmark):
       result = benchmark(lambda: client.get("/api/v1/suppliers"))
       assert result.elapsed_time < 0.2  # 200ms
   ```

2. **数据库查询性能**
   ```python
   def test_supplier_query_with_1000_records():
       # 插入1000条数据
       # 测试查询时间 < 100ms
   ```

3. **并发请求测试**
   ```python
   def test_concurrent_100_requests():
       with ThreadPoolExecutor(max_workers=100) as executor:
           futures = [executor.submit(get_supplier) for _ in range(100)]
           # 所有请求成功，无超时
   ```

**基准指标**:
| 端点 | 目标响应时间 |
|------|--------------|
| GET /api/v1/suppliers | < 200ms |
| POST /api/v1/suppliers | < 300ms |
| GET /api/v1/dashboard/stats | < 150ms |
| 并发100请求 | 95% < 500ms |

#### Task 3.2: 性能优化 (P2)
**负责**: 开发工程师  
**时间**: 0.5天

**优化点**:

1. **数据库查询优化**
   ```python
   # BEFORE:
   suppliers = await session.execute(select(Supplier))
   for s in suppliers:
       contacts = await session.execute(select(Contact).where(Contact.supplier_id == s.id))
   
   # AFTER: 使用 selectinload
   suppliers = await session.execute(
       select(Supplier).options(selectinload(Supplier.contacts))
   )
   ```

2. **添加数据库索引**
   ```python
   # migration: add_supplier_indexes.py
   op.create_index('idx_supplier_code', 'suppliers', ['code'])
   op.create_index('idx_supplier_status', 'suppliers', ['status'])
   op.create_index('idx_supplier_risk_level', 'suppliers', ['risk_level'])
   ```

3. **API 响应缓存**
   ```python
   from fastapi_cache import FastAPICache
   from fastapi_cache.backends.redis import RedisBackend
   
   @router.get("/suppliers")
   @cache(expire=60)  # 缓存60秒
   async def list_suppliers(...):
       ...
   ```

**验收标准**:
- 所有关键端点响应时间 < 基准指标
- 数据库查询优化后 N+1 问题消除

---

### Day 6: 文档与自动化 (1天)

#### Task 4.1: API 文档导出 (P2)
**负责**: 开发工程师  
**时间**: 0.5天

**生成文档**:
```bash
# OpenAPI Schema 导出
python -c "
from src.api.app import create_app
import json
app = create_app()
with open('docs/api/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
"

# 生成 Markdown 文档
pip install openapi-to-markdown
openapi-to-markdown docs/api/openapi.json > docs/api/API_REFERENCE.md
```

**创建文件**:
- `docs/api/openapi.json` - OpenAPI 3.0 规范
- `docs/api/API_REFERENCE.md` - Markdown 格式文档
- `docs/api/POSTMAN_COLLECTION.json` - Postman 测试集合

#### Task 4.2: CI/CD 测试自动化 (P2)
**负责**: 开发工程师  
**时间**: 0.5天

**创建文件**:
`.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        run: |
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=term
      
      - name: Check coverage
        run: |
          coverage report --fail-under=85
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

### Day 7: 总结与验收 (1天)

#### Task 5.1: 完整回归测试 (P0)
**负责**: 开发工程师  
**时间**: 0.5天

**执行测试套件**:
```bash
# 1. 单元测试
pytest tests/ -v --cov=src --cov-report=term --cov-report=html

# 2. 集成测试
pytest tests/integration/ -v

# 3. 性能测试
pytest tests/performance/ -v --benchmark-only

# 4. 架构测试
pytest tests/architecture/ -v

# 5. 完整测试
pytest tests/ -v --tb=short
```

**验收标准**:
- ✅ 所有测试通过（0 failed, 0 errors）
- ✅ 覆盖率 ≥ 85%
- ✅ 性能测试达标
- ✅ 架构规则通过

#### Task 5.2: Week 3 总结报告 (P1)
**负责**: 开发工程师  
**时间**: 0.5天

**创建文件**:
`docs/week3/WEEK3_COMPLETION_REPORT.md`

**包含内容**:
1. **完成功能清单**
   - 修复的问题
   - 新增的测试
   - 性能优化成果

2. **测试报告**
   - 测试覆盖率对比（67% → 85%+）
   - 测试通过率对比
   - 性能基准数据

3. **API 文档**
   - OpenAPI 规范链接
   - Postman 测试集合

4. **技术债务**
   - Pydantic V2 迁移（242个warnings）
   - 待优化项

5. **Week 4 准备**
   - 本地 LLM 集成所需依赖
   - Ollama 安装指南
   - Qwen2.5 模型下载

---

## 📊 Week 3 验收标准

### 必须达成 (P0)
- [ ] **测试覆盖率 ≥ 85%**
- [ ] **所有测试通过** (0 failed, 0 errors)
- [ ] **新增集成测试 ≥ 50 个**
- [ ] **API 文档完整** (100% 端点文档化)
- [ ] **性能基准建立** (响应时间 < 目标值)

### 期望达成 (P1)
- [ ] 统一错误处理机制
- [ ] 数据库查询优化
- [ ] CI/CD 自动化配置
- [ ] Postman 测试集合

### 可选达成 (P2)
- [ ] API 响应缓存
- [ ] 性能优化 > 30%
- [ ] 完整的 API 文档站点

---

## 🔧 工具与命令

### 开发环境
```bash
# 激活虚拟环境
cd D:\LiuHao-AI-OS
.venv\Scripts\activate

# 安装开发依赖
pip install pytest pytest-cov pytest-asyncio pytest-benchmark
pip install black flake8 mypy
pip install fastapi-cache redis
```

### 测试命令
```bash
# 快速测试
pytest tests/ -v --tb=short -x

# 覆盖率测试
pytest tests/ --cov=src --cov-report=html
# 打开 htmlcov/index.html 查看详细报告

# 性能测试
pytest tests/performance/ --benchmark-only --benchmark-autosave

# 持续集成模式
pytest tests/ -v --cov=src --cov-report=term --cov-report=xml --junitxml=junit.xml
```

### 代码质量
```bash
# 格式化代码
black src/ tests/

# 检查代码风格
flake8 src/ --count --statistics

# 类型检查
mypy src/ --ignore-missing-imports
```

---

## 📅 时间线

| 日期 | 任务 | 产出 |
|------|------|------|
| Day 1 | 修复现有问题 + 统一错误处理 | 0 failed tests, exceptions.py, error_handlers.py |
| Day 2 | API 文档完善 | 所有端点文档化 |
| Day 3 | 集成测试（Supplier + Dashboard） | 25个新测试 |
| Day 4 | 集成测试（Auth + Error Handling） | 25个新测试 |
| Day 5 | 性能基准 + 优化 | 性能基准报告, 数据库索引 |
| Day 6 | 文档导出 + CI/CD | openapi.json, test.yml |
| Day 7 | 回归测试 + 总结报告 | WEEK3_COMPLETION_REPORT.md |

---

## 🎯 成功指标

**Week 3 完成后的系统状态**:

| 指标 | Week 2 结束 | Week 3 目标 | 改善 |
|------|-------------|-------------|------|
| 测试覆盖率 | 67% | ≥ 85% | +18% |
| 测试通过率 | 92.6% | 100% | +7.4% |
| 测试数量 | 541 | 600+ | +60 |
| API 文档完整度 | 60% | 100% | +40% |
| API 响应时间 | 未测试 | < 200ms | - |
| CI/CD | ❌ | ✅ | - |

**技术债务**:
- Pydantic V2 迁移 → Phase 4 处理
- Redis 缓存 → Phase 2 引入

---

**制定人**: Codex AI - 开发工程师  
**日期**: 2026-08-23  
**版本**: LiuHao AI-OS Y1.0  
**状态**: 等待执行
