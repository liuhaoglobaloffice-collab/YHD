# Week 4 Day 4: RAG 基础实现

**日期**: 2026-08-24
**任务**: 实现检索增强生成 (RAG) Pipeline

---

## 📋 任务清单

### 1. 文档分块 (Chunking) (30分钟)
- [ ] 创建 `src/ai/chunking.py`
- [ ] 实现 `RecursiveCharacterTextSplitter`
- [ ] 支持重叠窗口
- [ ] 元数据保留

### 2. RAG Pipeline 实现 (60分钟)
- [ ] 创建 `src/ai/rag.py` (已存在，需完善)
- [ ] 实现 `RAGPipeline` 类
- [ ] 查询处理
- [ ] 文档检索
- [ ] 上下文构建
- [ ] LLM 生成

### 3. 简单演示脚本 (30分钟)
- [ ] 创建 `scripts/demo_rag.py`
- [ ] 加载示例文档
- [ ] 执行问答
- [ ] 展示检索结果

### 4. 单元测试 (30分钟)
- [ ] 测试文档分块
- [ ] 测试 RAG pipeline
- [ ] 端到端测试

---

## 🎯 RAG Pipeline 架构

```
用户查询
   ↓
查询理解 (可选)
   ↓
向量化查询
   ↓
向量检索 (ChromaDB)
   ↓
Top-K 文档
   ↓
上下文构建
   ↓
Prompt 工程
   ↓
LLM 生成 (Ollama)
   ↓
回答 + 来源引用
```

---

## 📦 预期交付物

1. `src/ai/chunking.py` - 文档分块工具
2. `src/ai/rag.py` - RAG Pipeline (完善)
3. `scripts/demo_rag.py` - RAG 演示脚本
4. `tests/ai/test_rag.py` - RAG 单元测试
5. `docs/WEEK4_DAY4_REPORT.md` - 完成报告

---

## ⏰ 时间规划

- 总计: 2.5小时
- 开始: 2026-08-24 10:50
- 预计完成: 2026-08-24 13:20

---

## 📊 成功标准

1. ✅ 文档分块工作正常
2. ✅ RAG pipeline 端到端运行
3. ✅ 演示脚本展示问答功能
4. ✅ 回答引用来源文档
5. ✅ 单元测试通过率 >80%
