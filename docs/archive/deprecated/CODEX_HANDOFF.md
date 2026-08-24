# LiuHao AI OS Codex Handoff

> **🔄 如果这是新的 Codex 窗口，请先读取本文件，然后继续开发。**

**创建时间**: 2026-08-22 14:58:00  
**目的**: 快速接管项目开发

---

## 🚨 立即阅读

**如果你是新的 Codex 对话窗口**，请按以下顺序操作：

### 1️⃣ 首先读取上下文文件

```bash
打开并阅读: docs/CODEX_CONTEXT.md
```

**这个文件包含**：
- 完整的项目状态
- 当前开发阶段
- 测试状态
- 下一步行动
- 重要规则

⏱️ **预计阅读时间**: 5分钟

---

### 2️⃣ 理解当前状态

**项目**: LiuHao AI OS Ultimate Architecture  
**目标**: AI 外贸自主运营操作系统

**当前阶段**: Stage 1 Phase 1 Step 1A 稳定化

**测试状态**:
```yaml
总测试: 498
通过: 327
失败: 171
通过率: 65.7%
```

**正在进行**:
- 修复 ProviderGateway 测试失败
- 提升测试通过率到 80%+

---

### 3️⃣ 确认重要规则

**⚠️ 绝对不允许**:
```yaml
❌ 不允许推翻 V1-V10 能力
❌ 不允许重新设计架构路线
❌ 不允许从零重建
❌ 不允许推翻核心设计理念
```

**✅ 必须遵守**:
```yaml
✅ 沿着 LiuHao AI OS 路线升级
✅ 增量优化而非重构
✅ 测试驱动开发
✅ 文档同步更新
```

---

### 4️⃣ 验证环境

运行以下命令验证环境：

```bash
# 进入项目目录
cd D:\LiuHao-AI-OS

# 验证Python版本
python --version  # 应该是 3.11+

# 运行测试
python -m pytest tests/ -v --tb=short

# 查看测试通过率
python -m pytest tests/ -v | grep -E "passed|failed"
```

预期输出：
```
327 passed, 171 failed in X.XXs
```

---

### 5️⃣ 查看下一步行动

**立即行动**（从 `CODEX_CONTEXT.md` 的 Next Actions）:

1. **修复 ProviderGateway 测试**
   - 文件: `src/ai/providers.py`
   - 问题: 不支持延迟初始化
   - 预计时间: 30分钟

2. **继续测试修复**
   - 目标: 80%+ 通过率
   - 预计时间: 2-3小时

---

### 6️⃣ 开始工作

**推荐工作流程**:

```yaml
步骤1: 运行测试
  python -m pytest tests/test_ai/test_providers.py::TestProviderGateway::test_register_provider -v

步骤2: 查看失败原因
  阅读测试输出

步骤3: 修复代码
  修改 src/ai/providers.py

步骤4: 验证修复
  重新运行测试

步骤5: 更新文档
  更新 docs/CODEX_CONTEXT.md
```

---

## 📚 关键文档快速索引

### 必读文档（优先级从高到低）

1. **docs/CODEX_CONTEXT.md** ⭐⭐⭐
   - 完整的项目上下文
   - 当前状态和下一步行动
   - **必须先读这个**

2. **docs/MERGE_OPTIMIZATION_SUMMARY.md** ⭐⭐
   - 6次合并优化总结
   - 架构演进历史
   - 了解项目全貌

3. **README.md** ⭐
   - 项目基本介绍
   - 快速开始指南

### 架构文档（可选，深入了解）

```yaml
核心架构:
  - docs/architecture/ULTIMATE_ARCHITECTURE_CONSOLIDATION.md
  - docs/architecture/IMPLEMENTATION_ROADMAP.md
  - docs/architecture/ZERO_TOKEN_ARCHITECTURE.md
  - docs/architecture/HOME_SERVER_DEPLOYMENT.md

增强点:
  - docs/architecture/enhancements/*.md

代码实现:
  - docs/architecture/implementation/*.md
```

---

## 🎯 快速决策树

### 我应该做什么？

```
开始 → 读取 CODEX_CONTEXT.md
       ↓
    了解当前状态
       ↓
    查看 Next Actions
       ↓
    /           \
有明确任务？    没有明确任务？
   ↓               ↓
执行任务        运行测试，分析失败
   ↓               ↓
验证结果        选择最紧急的修复
   ↓               ↓
更新文档        执行修复
   ↓               ↓
   ← ← ← ← ← ← ← ← 
```

---

## 🔍 常见问题

### Q1: 我忘记了项目的目标是什么？

**A**: 打造 AI 外贸自主运营操作系统，具备：
- 零Token运行（不依赖外部API付费）
- Multi-Agent协同
- 能量驱动系统
- 完全本地化部署

---

### Q2: 我不确定是否可以修改某个文件？

**A**: 遵循规则：
- ✅ 可以修改任何文件进行 **增量优化**
- ❌ 不能删除或替换 **V1-V10 的核心能力**
- ✅ 可以扩展功能
- ❌ 不能重新设计架构路线

**判断标准**: 如果修改会导致现有功能不可用，则不允许。

---

### Q3: 测试失败了，我应该怎么办？

**A**: 
1. 先理解失败原因（读测试输出）
2. 不要急于重构，先定点修复
3. 修复一个验证一个
4. 确保不引入新的失败

---

### Q4: 我需要添加新功能，从哪里开始？

**A**:
1. 确认不与 V1-V10 冲突
2. 查看是否符合 Stage/Phase 路线
3. 先写测试，后写代码
4. 完成后更新文档

---

### Q5: 文档太多了，我应该读哪些？

**A**: 优先级：
1. **必读**: `CODEX_CONTEXT.md`（本项目状态）
2. **推荐**: `MERGE_OPTIMIZATION_SUMMARY.md`（了解演进）
3. **可选**: 架构文档（深入理解）

---

## 🛠️ 工具和命令

### 测试相关

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块
python -m pytest tests/test_ai/ -v

# 运行特定测试
python -m pytest tests/test_ai/test_providers.py::TestProviderGateway::test_register_provider -v

# 只看失败的测试
python -m pytest tests/ -v --tb=short | grep FAILED

# 查看覆盖率
python -m pytest tests/ --cov=src --cov-report=html
```

### 代码质量

```bash
# 类型检查
mypy src/

# 代码格式化
black src/ tests/

# 代码质量检查
pylint src/
```

### 快速导航

```bash
# 查看项目结构
tree src/ -L 2

# 查看最近修改
git log --oneline -10

# 查看当前状态
git status
```

---

## 📊 项目结构速览

```
LiuHao-AI-OS/
├── docs/                    # 📚 文档目录
│   ├── CODEX_CONTEXT.md    # ⭐ 项目上下文（必读）
│   ├── CODEX_HANDOFF.md    # ⭐ 本文件
│   ├── MERGE_OPTIMIZATION_SUMMARY.md
│   └── architecture/        # 架构文档
│
├── src/                     # 💻 源代码
│   ├── ai/                 # AI核心模块
│   ├── api/                # FastAPI接口
│   ├── core/               # 核心功能
│   ├── identity/           # 身份认证
│   ├── knowledge/          # 知识中心
│   ├── security/           # 安全模块
│   ├── tasks/              # 任务系统
│   ├── workflow/           # 工作流引擎
│   └── workforce/          # 劳动力管理
│
└── tests/                   # 🧪 测试套件
    ├── test_ai/            # AI模块测试
    ├── test_api/           # API测试
    └── ...
```

---

## ⚡ 快速启动检查清单

使用这个检查清单快速进入工作状态：

```yaml
□ 1. 打开项目目录
     cd D:\LiuHao-AI-OS

□ 2. 读取上下文
     打开 docs/CODEX_CONTEXT.md

□ 3. 了解当前状态
     - 当前阶段: Stage 1 Phase 1 Step 1A
     - 测试通过率: 65.7%
     - 正在修复: ProviderGateway 测试

□ 4. 运行测试验证
     python -m pytest tests/ -v

□ 5. 查看 Next Actions
     从 CODEX_CONTEXT.md 获取

□ 6. 确认 Important Rules
     - 不推翻 V1-V10
     - 不重新设计路线
     - 增量优化

□ 7. 开始工作
     执行 Next Actions 中的第一个任务

□ 8. 完成后更新文档
     更新 CODEX_CONTEXT.md
```

---

## 🎓 学习路径

### 如果你想深入了解项目

**第1天**:
```yaml
1. 读取 CODEX_CONTEXT.md（了解现状）
2. 读取 MERGE_OPTIMIZATION_SUMMARY.md（了解演进）
3. 运行测试（熟悉测试套件）
4. 修复1-2个简单的测试失败
```

**第2-3天**:
```yaml
1. 阅读核心架构文档
2. 理解 V1-V10 能力
3. 理解 Stage 1-4 路线
4. 继续修复测试
```

**第4-7天**:
```yaml
1. 开始实现新功能
2. 遵循 Phase 0-4 路线
3. 保持测试通过率
4. 更新文档
```

---

## 📞 需要帮助？

### 如果遇到困惑

1. **再次阅读** `CODEX_CONTEXT.md`
2. **查看** `Next Actions` 部分
3. **运行测试** 了解实际状态
4. **查看最近改动** `git log`

### 记住

> **不要猜测，而是查看文档和代码！**  
> **不要重构，而是增量优化！**  
> **不要推翻，而是沿着路线升级！**

---

## 🎯 成功标准

**你成功接管项目的标志**:

```yaml
✅ 我理解了项目目标
✅ 我知道当前在 Stage 1 Phase 1 Step 1A
✅ 我知道测试通过率是 65.7%
✅ 我知道下一步要修复 ProviderGateway 测试
✅ 我记住了不能推翻 V1-V10
✅ 我理解了能量系统替代Token的理念
✅ 我知道如何运行测试
✅ 我知道完成任务后要更新 CODEX_CONTEXT.md
```

如果以上都能确认，你已经成功接管！开始工作吧！🚀

---

## 🔄 交接流程

### 当你需要交接给下一个 Codex 窗口时

**在离开前**:

```yaml
1. 完成当前任务或达到一个稳定点

2. 更新 CODEX_CONTEXT.md:
   - Current Development Status
   - Test Status
   - Recent Changes
   - Next Actions

3. 运行测试确认状态:
   python -m pytest tests/ -v

4. 记录未完成的工作在 Next Actions

5. 提交代码（如果使用git）:
   git add .
   git commit -m "描述你的修改"
   git push
```

---

**创建时间**: 2026-08-22 14:58:00  
**维护者**: Codex AI Assistant  
**版本**: 1.0.0

**记住**: 这不是文档，这是你的工作指南！按照它操作，你会成功接管项目！💪
