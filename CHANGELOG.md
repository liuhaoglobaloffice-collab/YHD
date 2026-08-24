# CHANGELOG - LiuHao AI-OS Y1.0

所有重要的项目变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵守 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### Week 4 - 本地 LLM 集成 (开始)
预计时间：2026-08-24 至 2026-08-31

## [Week 4 Day 1-2] - 2026-08-24

### Ollama本地LLM集成 ✅

#### 已完成
- ✅ **OllamaProvider实现** (+91行代码)
  - 异步chat completion
  - Token usage追踪
  - 完整错误处理
  - 惰性客户端加载
- ✅ **配置管理** (+4配置项)
  - ollama_host, ollama_default_model
  - ollama_timeout, ollama_enabled
- ✅ **单元测试** (260行, 9/10通过)
- ✅ **集成测试脚本** (240行)
  - 服务检测, 模型管理
  - 推理测试, 性能基准
  - UTF-8编码支持
- ✅ **依赖管理**
  - 安装 ollama>=0.6.2
  - 更新 requirements.txt

#### 代码统计
```
新增代码: 745行
  - OllamaProvider: 91行
  - Config: 4行
  - 单元测试: 260行
  - 集成脚本: 240行
  - Gateway测试: 150行
```

#### 下一步
- ✅ Week 4 Day 3 - ChromaDB向量数据库集成 (已完成)
- ✅ Week 4 Day 4 - RAG基础实现 (已完成)

---

## [Week 4 Day 4] - 2026-08-24

### RAG基础实现 ✅

#### 已完成
- ✅ **文档分块系统** (+269行)
  - RecursiveCharacterTextSplitter（智能分块）
  - SimpleTextSplitter（固定大小分块）
  - 支持中英文混合文本
  - 可配置 chunk_size/chunk_overlap
  - 元数据传递和索引追踪

- ✅ **RAG系统增强** (+20行重构)
  - 独立 Embedding Provider（解耦 Ollama）
  - 自动文档分块索引
  - ChromaDB 默认存储（持久化）
  - 标准化 ProviderRequest 接口
  - 支持流式/非流式生成

- ✅ **RAG演示脚本** (+270行)
  - 完整 RAG 流程演示
  - 5个示例文档（产品/AI员工/供应商/技术/计划）
  - 4个问答测试
  - 来源文档 + 相关度评分

- ✅ **单元测试** (+317行，18/18通过)
  - 7个分块器测试 ✅
  - 11个RAG系统测试 ✅
  - 测试通过率: 100%

#### 代码统计
```
新增代码: 876行
  - chunking.py: 269行
  - rag.py: +20行（重构）
  - demo_rag.py: 270行
  - test_rag.py: 317行

覆盖率:
  - chunking.py: 94%
  - rag.py: 82%
  - RAG模块总体: 88%
```

#### 技术亮点
1. 智能分块算法：优先在段落/句子边界分割，保持语义完整
2. 灵活 Embedding 切换：Ollama / ChromaDB / SentenceTransformers
3. ChromaDB 持久化：无需 PostgreSQL，自动保存向量
4. 分块元数据追踪：parent_doc_id, chunk_index, total_chunks

#### 质量指标
- 测试通过率: 100% (18/18) ✅
- 代码覆盖率: 88% (RAG模块) ✅
- P0/P1 Bug: 0 ✅

#### 下一步
- ⏳ Week 4 Day 5 - RAG优化 + Week 4总结

---

## [Week 3 Complete] - 2026-08-24

### Week 3 - API完善与测试加固 ✅
完成时间：2026-08-24 (1天完成)

#### 已完成
- ✅ **Supplier API扩展** (+939行代码)
  - validators.py (260行) - 7种数据验证规则
  - import_export.py (217行) - Excel/CSV导入导出
  - crud.py 扩展 (+310行) - 批量操作 + 高级搜索
  - supplier.py 路由扩展 (+152行) - 6个新REST端点
- ✅ **新增测试** (12个用例, 100%通过)
- ✅ **质量指标**
  - 测试通过率: 98.4% (545/554) ⬆️ +0.1%
  - 代码覆盖率: 68% ⬆️ +1%
  - P0/P1 Bug: 0个 ✅
- ✅ **Bug修复**
  - BUG-012: BusinessType枚举值不匹配
- ✅ **文档**
  - docs/WEEK3_SUMMARY.md - Week 3完成报告

#### 核心成果
```
新增REST端点：
  POST   /api/v1/suppliers/batch           - 批量创建
  PUT    /api/v1/suppliers/batch           - 批量更新
  DELETE /api/v1/suppliers/batch           - 批量删除
  POST   /api/v1/suppliers/import          - 导入Excel/CSV
  GET    /api/v1/suppliers/export          - 导出Excel/CSV
  GET    /api/v1/suppliers/advanced-search - 高级搜索
```

---

## [v1.0.0] - 2026-08-24

### Week 2 Day 5 - 演示数据生成 (2026-08-24)

#### 新增
- **演示数据脚本** (`scripts/seed_demo_data.py` - 475行)
  - 生成15个演示供应商（5家知名大企业、5家国际企业、5家中小企业）
  - 生成32个联系人
  - 生成49个证书
  - 执行15个风险评估
- **辅助脚本**
  - `scripts/run_risk_assessment.py` - 批量运行风险评估
  - `scripts/generate_token.py` - 生成JWT测试Token
  - `scripts/verify_dashboard_data.py` - 验证Dashboard数据完整性
# LiuHao AI-OS 更新日志

## [Unreleased] - 2026-08-23

### Added - Week 5 Day 2前端组件库

**组件库** (frontend/src/components/ui/):
- Button.tsx (67行) - 5种样式变体 (primary, secondary, outline, ghost, danger)
- Card.tsx (48行) - 3种变体 (default, glass, neon)
- Table.tsx (110行) - 泛型表格组件，支持排序、加载、空状态
- Modal.tsx (123行) - 模态框组件，支持ESC关闭、点击遮罩关闭
- Form.tsx (171行) - Input, TextArea, Select, Checkbox表单组件
- index.ts - 统一导出

**主题优化**:
- tailwind.config.js - 赛博朋克配色(cyber.blue, cyan, pink, purple)
- tailwind.config.js - 新增 neon-blue/cyan/pink 阴影效果
- tailwind.config.js - 新增 pulse-glow, slide-in 动画
- index.css - 深色模式样式，滚动条样式，选中文本样式
- index.css - .neon-text, .glass, .card-hover 工具类

**响应式布局**:
- DashboardLayout.tsx - 移动端侧边栏支持（待更新）
- Sidebar.tsx - 隐藏在移动端（hidden md:block）

### Stats
- 新增文件: 6个组件 + 2个配置文件
- 代码量: ~520行（组件）
- 组件覆盖: Button, Card, Table, Modal, 4种Form组件

### Next
- Week 5 Day 3: 四级菜单交互优化
- Week 5 Day 4: 状态管理(Zustand) + API集成
- Week 5 Day 5: 登录页面 + 认证流程

---

## [v1.0.0] - Phase 1 Week 4 Complete

### Week 4 - 本地LLM集成
- Ollama Provider + RAG System
- ChromaDB + Embeddings (SentenceTransformers, Ollama)
- Reranker (Score, MMR, LLM)
- Hybrid Search (BM25 + Vector)
- Query Expansion
- 新增代码: ~4,300行
- 测试覆盖率: AI模块 80%+

### Week 2-3 - 供应商智能数据层
- Supplier数据模型(4张表)
- CRUD服务(20+方法)
- Risk Agent AI
- Dashboard API
- 批量操作 + 高级搜索 + 导入导出

### System Status
- 测试通过: 599/615 (97.4%)
- P0/P1 Bug: 0
- 代码覆盖率: 38%（总体），AI模块80%+
