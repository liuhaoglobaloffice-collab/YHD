# Week 4 Day 3: pgvector 向量数据库集成

**日期**: 2026-08-24
**任务**: 实现 pgvector 向量存储

---

## 📋 任务清单

### 方案选择

考虑到当前系统使用SQLite，有两个方案：

#### 方案A: PostgreSQL + pgvector (生产级)
- ✅ 高性能向量搜索
- ✅ 事务支持
- ❌ 需要安装PostgreSQL
- ❌ 环境配置复杂

#### 方案B: SQLite + sqlite-vss (轻量级)
- ✅ 无需额外服务
- ✅ 与当前SQLite一致
- ✅ 快速验证RAG
- ⏳ 性能略低于pgvector

**决策**: 先实现方案B (sqlite-vss)，为Week 4 RAG提供快速支持。
Phase 2时可升级到PostgreSQL+pgvector。

---

## 🎯 sqlite-vss 集成任务

### 1. 安装依赖 (10分钟)
- [ ] 安装 sqlite-vss: `pip install sqlite-vss`
- [ ] 更新 requirements.txt
- [ ] 验证安装

### 2. 实现 SqliteVssVectorStore (60分钟)
- [ ] 在 `src/ai/vector_store.py` 中实现类
- [ ] 实现 `add_document()`
- [ ] 实现 `add_documents()` 批量添加
- [ ] 实现 `search()` 向量搜索
- [ ] 实现 `delete_document()`
- [ ] 实现 `clear()` 清空

### 3. 嵌入功能 (30分钟)
- [ ] 创建 `src/ai/embeddings.py`
- [ ] 实现 `EmbeddingProvider` 抽象类
- [ ] 实现 `OllamaEmbedding` (使用Ollama的embedding模型)
- [ ] 实现 fallback到 `SentenceTransformerEmbedding`

### 4. 单元测试 (30分钟)
- [ ] 创建 `tests/ai/test_vector_store.py`
- [ ] 测试文档添加
- [ ] 测试向量搜索
- [ ] 测试相似度排序
- [ ] 测试删除操作

### 5. 集成测试脚本 (20分钟)
- [ ] 创建 `scripts/test_vector_search.py`
- [ ] 测试完整的嵌入→存储→检索流程
- [ ] 性能基准测试

---

## 📦 预期交付物

1. `src/ai/vector_store.py` - 新增 SqliteVssVectorStore
2. `src/ai/embeddings.py` - 新增嵌入providers
3. `tests/ai/test_vector_store.py` - 单元测试
4. `scripts/test_vector_search.py` - 集成测试脚本
5. `requirements.txt` - 更新依赖
6. `docs/WEEK4_DAY3_REPORT.md` - 完成报告

---

## 🔧 技术方案

### sqlite-vss 架构

```
文档文本
   ↓
Embedding Provider (Ollama/SentenceTransformer)
   ↓
向量 (768维/1024维)
   ↓
SqliteVssVectorStore
   ↓
SQLite + vss 扩展
```

### 数据模型

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS vss_documents USING vss0(
    embedding(768)  -- 向量维度
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## ⏰ 时间规划

- 总计: 2.5小时
- 开始: 2026-08-24 09:10
- 预计完成: 2026-08-24 11:40

---

## 📊 成功标准

1. ✅ SqliteVssVectorStore 实现完整
2. ✅ 嵌入功能正常工作
3. ✅ 单元测试通过率 100%
4. ✅ 集成测试脚本可运行
5. ✅ 向量搜索准确率 >90%

---

## 🎯 Week 4 Day 3 目标

完成向量存储基础设施，为Day 4-5的RAG实现提供支持。
