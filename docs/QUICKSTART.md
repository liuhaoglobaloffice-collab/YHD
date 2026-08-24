# LiuHao AI-OS 快速开始

**更新**: 2026-08-23  
**版本**: Y1.0

---

## 🚀 启动项目

### 1. 启动API服务器

```powershell
cd D:\LiuHao-AI-OS

# 设置环境变量
$env:SECRET_KEY='H0OOgF7Hu8G40TtZnN_QCyAPGInurI9X6K39GUXTTBQ'
$env:JWT_SECRET_KEY='FD567ckE0cOXIiwBhkt3YNInrIn62jPHneF-JAIWBwI'

# 启动服务器（开发模式）
python -B -m uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```

**访问**:
- API: http://localhost:8000
- Swagger文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

---

## 🧪 运行测试

### 完整测试

```powershell
cd D:\LiuHao-AI-OS

# 运行所有测试（排除性能测试）
pytest tests/ --ignore=tests/performance/ -v

# 生成覆盖率报告
pytest tests/ --ignore=tests/performance/ --cov=src --cov-report=html

# 查看覆盖率
start htmlcov/index.html
```

### 特定模块测试

```powershell
# Supplier模块
pytest tests/business/test_supplier_crud.py -v

# Identity模块
pytest tests/identity/ -v

# API测试
pytest tests/api/ -v
```

---

## 🗄️ 数据库管理

### 查看当前迁移

```powershell
cd D:\LiuHao-AI-OS

# 查看当前版本
alembic current

# 查看迁移历史
alembic history
```

### 创建新迁移

```powershell
# 自动生成迁移（检测模型变化）
alembic revision --autogenerate -m "描述"

# 手动创建迁移
alembic revision -m "描述"
```

### 应用迁移

```powershell
# 升级到最新版本
alembic upgrade head

# 升级一步
alembic upgrade +1

# 降级一步
alembic downgrade -1
```

---

## 🔑 主账号管理

### 创建主账号

```powershell
# API请求
curl -X POST http://localhost:8000/api/v1/master/register `
  -H "Content-Type: application/json" `
  -d '{
    "username": "boss",
    "email": "boss@liuhao.ai",
    "password": "SecurePassword123",
    "display_name": "鎏灏老板"
  }'
```

### 主账号登录

```powershell
curl -X POST http://localhost:8000/api/v1/master/login `
  -H "Content-Type: application/json" `
  -d '{
    "username": "boss",
    "password": "SecurePassword123"
  }'
```

### 创建子账号

```powershell
curl -X POST http://localhost:8000/api/v1/master/sub-accounts `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{
    "username": "employee1",
    "email": "emp1@liuhao.ai",
    "password": "Employee123",
    "display_name": "员工1号"
  }'
```

---

## 📦 Supplier API 使用

### 创建供应商

```powershell
curl -X POST http://localhost:8000/api/v1/suppliers `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -d '{
    "name": "优质供应商有限公司",
    "supplier_type": "manufacturer",
    "industry": "electronics",
    "website": "https://example.com",
    "email": "contact@example.com"
  }'
```

### 查询供应商列表

```powershell
curl http://localhost:8000/api/v1/suppliers `
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查询单个供应商

```powershell
curl http://localhost:8000/api/v1/suppliers/{supplier_id} `
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🛠️ 开发工具

### 清理字节码缓存

```powershell
cd D:\LiuHao-AI-OS

# Python清理
python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
```

### 代码质量检查

```powershell
# Flake8检查
flake8 src/ --count --statistics

# 类型检查（如果配置了mypy）
mypy src/
```

### 查看API路由

```powershell
# 使用验证脚本
python -B verify_all_apis.py
```

---

## 🐛 故障排查

### 问题: API返回404

**解决**:
1. 清理字节码缓存
2. 使用 `-B` 标志启动服务器
3. 检查路由注册：`src/api/routes/__init__.py`

### 问题: 数据库连接错误

**检查**:
1. 数据库文件是否存在：`data/liuhao_ai_os.db`
2. 迁移是否应用：`alembic current`
3. 权限是否正确

### 问题: 测试失败

**诊断**:
```powershell
# 运行单个测试并查看详细输出
pytest tests/path/to/test.py::TestClass::test_method -vv -s

# 查看失败测试的完整traceback
pytest tests/ -v --tb=long
```

---

## 📚 有用的命令

### 项目状态

```powershell
# 查看git状态
git status

# 查看最新提交
git log --oneline -10

# 查看分支
git branch
```

### 依赖管理

```powershell
# 查看已安装包
pip list

# 更新requirements
pip freeze > requirements.txt

# 安装依赖
pip install -r requirements.txt
```

---

## 📖 文档链接

- [架构文档](./ARCHITECTURE.md)
- [项目状态](./PROJECT_STATUS.md)
- [开发总结](./DEV_SUMMARY_2026-08-23.md)
- [Week3验收报告](./WEEK3_ARCHITECTURE_STABILIZATION_REPORT.md)
- [主路线图](./ROADMAP_FREEZE.md)

---

## ⚡ 快速命令参考

```powershell
# 启动服务器
python -B -m uvicorn src.api.app:create_app --factory --reload

# 运行测试
pytest tests/ --ignore=tests/performance/ -v

# 清理缓存
python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"

# 查看API
python -B verify_all_apis.py

# 数据库迁移
alembic upgrade head
```

---

**快速开始完成！现在可以开始开发了！** 🎉
