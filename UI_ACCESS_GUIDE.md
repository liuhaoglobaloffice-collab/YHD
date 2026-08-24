# 鎏灏 AI-OS UI 操作平台 - 使用指南

## 📊 当前状态

### ✅ 已完成
1. **前端 UI 平台**: 供应商智能管理界面
   - 供应商列表页面 (带搜索、筛选、统计)
   - 响应式设计 (桌面+移动端)
   - 风险等级标识
   - CRUD 操作按钮
   - 路由与菜单配置完整

2. **后端 API**: Supplier Intelligence 模块
   - 5 个 REST API 端点全部工作
   - 认证系统正常
   - RBAC 权限控制已实现
   - 审计日志枚举已添加

3. **服务运行状态**
   - ✅ 后端: http://localhost:8000 (运行中)
   - ✅ 前端: http://localhost:3001 (运行中)

---

## 🚀 访问 UI 操作平台

### 方式 1: 直接打开前端
```
浏览器访问: http://localhost:3001
```

### 方式 2: 访问供应商管理页面
```
路径: http://localhost:3001/business/supplier/list
```

**默认测试账号**:
- 用户名: `testuser`
- 密码: `testpass123`

---

## ⚙️ API 端点清单

### Supplier API (Module 48)
```
Base URL: http://localhost:8000/api/v1

端点:
- GET    /suppliers              # 获取供应商列表
- POST   /suppliers              # 创建供应商
- GET    /suppliers/{id}         # 获取单个供应商
- PUT    /suppliers/{id}         # 更新供应商
- DELETE /suppliers/{id}         # 删除供应商
```

所有供应商 API 需要认证 token 和对应权限:
- `supplier:read` - 查看权限
- `supplier:create` - 创建权限
- `supplier:update` - 更新权限
- `supplier:delete` - 删除权限

---

## 🔐 权限配置

### 问题
新注册用户默认没有供应商模块权限，会返回:
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Insufficient permissions. Required: supplier:read"
  }
}
```

### 解决方案

需要给用户分配权限。有以下几种方式:

#### 方式 1: 通过超级管理员账号分配
如果系统有 admin 账号，登录后通过角色管理给用户分配供应商权限。

#### 方式 2: 直接修改数据库 (开发测试用)
```python
# 给用户分配所有供应商权限
from src.identity.models import User, Permission, Role
from src.api.dependencies.database import get_db

# 创建或获取供应商权限
permissions = [
    "supplier:read",
    "supplier:create",
    "supplier:update",
    "supplier:delete"
]

# 给用户的角色添加这些权限
# (需要在数据库操作脚本中实现)
```

#### 方式 3: 修改 API 权限依赖 (临时开发测试)
临时移除 `require_permission` 依赖，仅用于开发测试:

```python
# src/api/routes/supplier.py
# 临时注释掉权限检查 (仅测试用)
@router.get("", response_model=List[SupplierResponse])
async def list_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # _: None = Depends(require_permission("supplier:read")),  # 临时注释
):
    ...
```

---

## 🎨 前端界面特性

### 供应商列表页面
- **统计卡片**: 总供应商数、活跃供应商、高风险供应商、本月新增
- **搜索**: 按名称/联系人搜索
- **筛选**: 
  - 状态: 全部/活跃/inactive/黑名单
  - 类型: 全部/制造商/贸易商/代理商/分销商/服务商
- **表格列**:
  - 供应商名称
  - 业务类型
  - 联系人
  - 联系方式
  - 风险等级 (带颜色标识)
  - 状态
  - 操作按钮 (查看/编辑/删除)
- **操作**:
  - 添加供应商
  - 查看详情
  - 编辑信息
  - 删除供应商

### Mock 数据
前端包含 3 个示例供应商数据，用于 UI 展示。实际使用时会连接后端 API。

---

## 📁 关键文件位置

### 前端
```
frontend/
├── src/pages/supplier/
│   └── SupplierListPage.tsx       # 供应商列表页面 (主界面)
├── src/App.tsx                    # 路由配置
└── src/config/menuConfig.ts       # 菜单配置
```

### 后端
```
src/
├── api/routes/supplier.py         # Supplier API 路由
├── api/routes/__init__.py         # API router 注册
├── business/supplier/
│   ├── models.py                  # 数据模型
│   └── crud.py                    # CRUD 操作
└── identity/audit.py              # 审计枚举 (已添加 supplier 事件)
```

### 文档
```
docs/
├── deliverables/
│   └── UI_DELIVERY_REPORT.md      # UI 交付报告
└── frontend/
    ├── UI_README.md               # 技术文档
    └── UI_GUIDE.html              # 用户指南
```

---

## 🧪 测试 API

### 完整测试脚本
已创建测试脚本: `test_api_flow.py`

运行:
```bash
cd D:\LiuHao-AI-OS
python test_api_flow.py
```

测试流程:
1. 注册用户
2. 登录获取 token
3. 查询供应商列表
4. 创建新供应商
5. 查询单个供应商

---

## 🔄 下一步工作

### 优先级 P1: 权限配置
- [ ] 创建供应商角色 (Supplier Manager)
- [ ] 分配默认权限给测试用户
- [ ] 或配置超级管理员账号

### 优先级 P2: Week 2 主任务继续
根据 Week 2 架构检查修正指令:
- [✅] 任务 1: Supplier API 路由注册 (已完成)
- [ ] 任务 2: Migration 测试修复 (BUG-011)
- [ ] 任务 3: 提升测试覆盖率 68%→80%+
- [ ] 任务 4: 代码质量检查

### 优先级 P3: UI 功能增强
- [ ] 供应商详情页面
- [ ] 供应商创建/编辑表单
- [ ] 智能分析页面 (图表展示)
- [ ] 实际连接后端 API (替换 Mock 数据)

---

## 📞 技术支持

### 服务器命令
```bash
# 启动后端 (开发模式)
cd D:\LiuHao-AI-OS
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

# 启动前端
cd D:\LiuHao-AI-OS\frontend
npm run dev

# 运行测试
pytest tests/ --ignore=tests/performance -v
```

### 常见问题
1. **前端打不开**: 检查端口 3001 是否被占用
2. **后端 404**: 确认服务器已启动且 API 路由已注册
3. **401 未认证**: 需要先登录获取 token
4. **403 权限不足**: 用户需要对应的供应商权限

---

**最后更新**: 2026-08-23  
**版本**: Y1.0 - Week 2
