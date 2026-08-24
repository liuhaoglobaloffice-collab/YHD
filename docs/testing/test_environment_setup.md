# 🛠️ 测试环境配置文档

**创建时间**: 2026-08-23  
**测试工程师**: QA Team  
**项目**: LiuHao AI-OS v1.0  

---

## ✅ 环境验证结果

### 1. 基础环境

| 工具 | 版本 | 状态 | 用途 |
|------|------|------|------|
| Python | 3.13.15 | ✅ 已安装 | 运行测试框架 |
| pytest | 9.1.1 | ✅ 已安装 | 单元/集成测试 |
| curl | 8.13.0 | ✅ 已安装 | API 快速验证 |
| SQLite3 | Built-in | ✅ 可用 | 数据库验证 |
| Git | - | ⏭️ 待检查 | 版本控制 |

### 2. 服务器状态

```bash
# 生产服务器
URL: http://localhost:8000
状态: ✅ 运行中
响应: {"name":"LiuHao AI OS","version":"1.0.0","status":"running"}
工作进程: 4 workers (Uvicorn)
```

### 3. 数据库

```
文件: liuhao_ai_os_production.db
大小: 401 KB
用户: 3 (admin, testuser, sysadmin)
状态: ✅ 正常
```

---

## 📋 API 测试工具选择

### 推荐方案：**Postman** （免费版）

**优势**：
- ✅ 免费版功能完整
- ✅ 支持集合（Collections）管理
- ✅ 环境变量配置
- ✅ 自动化测试（Newman）
- ✅ 导出/导入测试用例
- ✅ Mock 服务器

**安装**：
```bash
# Windows
下载：https://www.postman.com/downloads/
或使用 winget：
winget install Postman.Postman
```

### 备选方案：**Apifox** （国产）

**优势**：
- ✅ 中文界面
- ✅ 集成文档/Mock/自动化
- ✅ 团队协作
- ✅ API 导入（Swagger/OpenAPI）

**安装**：
```bash
# 下载
https://www.apifox.cn/
```

**决策**：使用 **Postman**（行业标准，便于未来团队扩展）

---

## 🗄️ 数据库工具选择

### 推荐方案：**DBeaver** （免费开源）

**优势**：
- ✅ 完全免费
- ✅ 支持 SQLite/PostgreSQL/MySQL
- ✅ SQL 编辑器 + 代码高亮
- ✅ 数据可视化
- ✅ ER 图生成
- ✅ 查询结果导出（CSV/Excel）

**安装**：
```bash
# Windows
下载：https://dbeaver.io/download/
或使用 winget：
winget install dbeaver.dbeaver
```

### 备选方案：**SQLite Browser**

**优势**：
- ✅ 专为 SQLite 设计
- ✅ 轻量级
- ✅ 便携版可用

**安装**：
```bash
https://sqlitebrowser.org/dl/
```

**决策**：使用 **DBeaver**（未来可能迁移到 PostgreSQL，工具通用性好）

---

## 🐛 Bug 管理工具选择

### 推荐方案：**飞书多维表格** （免费）

**优势**：
- ✅ 完全免费
- ✅ 轻量级、易上手
- ✅ 支持字段类型（单选、多选、日期、附件）
- ✅ 自动化通知
- ✅ 导出 Excel
- ✅ 在线协作

**表格字段设计**：
```
| 字段名       | 类型     | 选项/说明                          |
|--------------|----------|------------------------------------|
| Bug ID       | 文本     | 格式：BUG-001                      |
| 标题         | 文本     | 简短描述（<50字）                  |
| 优先级       | 单选     | P0/P1/P2/P3                        |
| 状态         | 单选     | New/In Progress/Fixed/Verified/Closed |
| 所属模块     | 单选     | Auth/RBAC/Knowledge/Task/Workflow  |
| 发现人       | 文本     | QA Team                            |
| 指派给       | 文本     | Developer Name                     |
| 发现日期     | 日期     | 自动记录                           |
| 修复日期     | 日期     | 开发完成时填写                     |
| 详细描述     | 长文本   | 完整复现步骤                       |
| 预期结果     | 长文本   | -                                  |
| 实际结果     | 长文本   | -                                  |
| 环境         | 文本     | Python 3.13, Windows/Linux         |
| 截图/日志    | 附件     | -                                  |
| 修复方案     | 长文本   | 开发填写                           |
```

**决策**：使用 **飞书多维表格**

### 备选方案：**Excel**

适用于：
- ✅ 离线工作
- ✅ 无需团队协作
- ✅ 简单项目

---

## 📦 测试工具安装清单

### 立即安装（Day 3 上午）

```bash
# 1. Postman（API 测试）
winget install Postman.Postman

# 2. DBeaver（数据库查看）
winget install dbeaver.dbeaver

# 3. 验证 Git
git --version
```

### 可选工具（按需安装）

```bash
# Apifox（备选 API 工具）
https://www.apifox.cn/

# SQLite Browser（备选 DB 工具）
https://sqlitebrowser.org/

# Jira/禅道（企业级 Bug 管理，需付费或自建）
```

---

## 🔧 测试环境配置步骤

### Step 1: 验证 Python 环境

```bash
cd D:\LiuHao-AI-OS
python --version  # 应输出 3.13.15
pytest --version  # 应输出 9.1.1

# 运行快速验证测试
pytest tests/ --ignore=tests/performance --tb=line -q
# 预期结果：484/484 passed
```

### Step 2: 配置 Postman

1. **创建 Collection**：`LiuHao AI-OS Tests`
2. **配置环境变量**：
   ```json
   {
     "base_url": "http://localhost:8000",
     "admin_token": "从登录接口获取",
     "test_user_token": "从登录接口获取"
   }
   ```
3. **导入第一个测试**：健康检查
   ```
   GET {{base_url}}/
   Expected: {"name":"LiuHao AI OS","version":"1.0.0","status":"running"}
   ```

### Step 3: 配置 DBeaver

1. **新建连接**：SQLite
2. **数据库文件**：`D:\LiuHao-AI-OS\liuhao_ai_os_production.db`
3. **测试连接**：查看 `users` 表
4. **保存查询**：常用验证 SQL

### Step 4: 配置飞书多维表格

1. **创建多维表格**：`LiuHao AI-OS Bug Tracker`
2. **导入现有 9 个 Bug**（从 `docs/testing/bug_list.md`）
3. **设置通知**：P0/P1 Bug 自动通知开发

---

## ✅ 环境验证检查表

**Day 3 上午完成目标**：

- [x] Python/pytest 可用 ✅
- [x] 服务器运行正常 ✅
- [x] 数据库文件可访问 ✅
- [ ] Postman 安装完成 ⏭️
- [ ] DBeaver 安装完成 ⏭️
- [ ] 飞书表格创建完成 ⏭️
- [ ] 导入现有 9 个 Bug ⏭️
- [ ] 环境配置文档归档 ✅

---

## 📞 故障排查

### 问题 1：服务器无响应

```bash
# 检查进程
Get-Process | Select-String python

# 重启服务器
cd D:\LiuHao-AI-OS
python start_production.py
```

### 问题 2：数据库锁定

```bash
# 关闭所有数据库连接
# 重启 DBeaver
# 确保没有多个 pytest 进程
```

### 问题 3：测试失败

```bash
# 清理缓存
pytest --cache-clear
rm -rf .pytest_cache .coverage htmlcov

# 重新运行
pytest tests/ --ignore=tests/performance -v
```

---

## 📊 环境配置完成标准

**验收标准**：
1. ✅ 所有工具安装完成
2. ✅ Postman 能成功调用健康检查接口
3. ✅ DBeaver 能查看数据库表
4. ✅ 飞书表格包含 9 个已知 Bug
5. ✅ pytest 命令能运行并通过 484 测试

**预计完成时间**：Day 3 上午（2 小时）

---

**下一步**：Day 3 下午 - 设计 Supplier CRUD 测试用例（20 cases）
