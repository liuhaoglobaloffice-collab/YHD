#!/usr/bin/env python3
"""
RAG 系统演示脚本
Week 4 Day 4

演示完整 RAG 流程：
1. 初始化系统
2. 添加示例文档
3. 查询问题
4. 显示答案和来源
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.embeddings import create_embedding_provider
from src.ai.providers import OllamaProvider, ProviderConfig, ProviderType
from src.ai.rag import RAGSystem
from src.ai.vector_store import ChromaVectorStore


# 示例文档内容
SAMPLE_DOCUMENTS = [
    {
        "text": """
鎏灏 AI-OS 是一个企业级 AI 操作系统，专为外贸企业设计。

核心特性：
1. 32 名 AI 员工，覆盖研发、销售、营销、运营等 8 大部门
2. 知识库管理：支持文档上传、分类、检索
3. 多租户系统：支持主子账号、Token 池管理、隐秘调度
4. 工作流引擎：支持 AI 协作流程设计和自动化执行

技术架构：
- 后端：Python + FastAPI + SQLAlchemy
- 前端：React + TypeScript + Tailwind CSS
- 向量数据库：ChromaDB
- 本地 LLM：Ollama + Qwen2.5 7B
        """,
        "metadata": {"source": "产品介绍", "category": "系统概述"},
    },
    {
        "text": """
鎏灏 AI-OS 的 AI 员工管理系统：

AI 员工分类：
- 研发部门：产品经理、架构师、开发工程师、测试工程师
- 销售部门：销售经理、销售代表、客户成功经理、商务拓展
- 营销部门：营销总监、内容营销、社交媒体专员、SEO 专家
- 运营部门：运营经理、数据分析师、供应链专员、质量管理

每个 AI 员工具备：
- 独立身份和角色定义
- 专业技能和知识库
- 任务执行能力
- 协作通信能力

管理功能：
- 员工列表查看
- 能力配置管理
- 绩效监控
- 任务分配
        """,
        "metadata": {"source": "AI 员工手册", "category": "功能详解"},
    },
    {
        "text": """
鎏灏 AI-OS 供应商管理模块：

Week 2 已完成功能：
1. 供应商数据模型（Supplier, SupplierContact, SupplierCertificate, SupplierRiskAssessment）
2. 完整 CRUD 操作（创建、读取、更新、删除）
3. 数据采集 Agent（Web Scraper Agent）
4. 风险评估 AI（Risk Assessment AI）

数据采集来源：
- 阿里巴巴国际站
- Made-in-China
- Global Sources
- 企业官网

风险评估维度：
- 信用风险（50%权重）
- 质量风险（30%权重）
- 交付风险（20%权重）

评估结果：
- 低风险（Low）：80-100 分
- 中风险（Medium）：50-79 分
- 高风险（High）：0-49 分
        """,
        "metadata": {"source": "供应商管理文档", "category": "业务模块"},
    },
    {
        "text": """
鎏灏 AI-OS 技术栈：

后端技术：
- 语言：Python 3.11+
- Web 框架：FastAPI
- ORM：SQLAlchemy 2.0 (async)
- 数据库：SQLite (开发环境), PostgreSQL (生产环境)
- 向量数据库：ChromaDB 1.5+
- 本地 LLM：Ollama + Qwen2.5 7B

前端技术：
- 框架：React 18
- 语言：TypeScript
- 样式：Tailwind CSS
- 状态管理：Context API
- 路由：React Router v6

AI 技术：
- LLM Provider：OpenAI / Claude / Ollama
- Embedding：mxbai-embed-large (Ollama) / Sentence Transformers
- 向量检索：ChromaDB
- RAG：自研 RAG 系统

测试：
- 单元测试：pytest + pytest-asyncio
- 代码覆盖率：pytest-cov
- 集成测试：TestClient (FastAPI)
        """,
        "metadata": {"source": "技术文档", "category": "开发指南"},
    },
    {
        "text": """
鎏灏 AI-OS Phase 1 开发计划（Week 2-8）：

Week 2: 供应商智能数据层
- Day 1-2: 数据模型设计与实现
- Day 3: 数据采集 Agent
- Day 4: 风险评估 AI + Dashboard API
- Day 5: 演示数据 + 总结

Week 3: API 完善与测试加固
- 完善 Business API
- 集成测试覆盖率 >85%
- 性能优化

Week 4: 本地 LLM 集成
- Day 1-2: Ollama 集成
- Day 3: ChromaDB 向量数据库
- Day 4: RAG 基础实现
- Day 5: RAG 优化与总结

Week 5: 前端项目搭建
- React 项目初始化
- 赛博朋克主题设计
- 四级菜单系统

Week 6: CEO Dashboard 核心页面
- 实时仪表板
- AI 员工管理界面
- 任务中心

Week 7: 供应商管理前端
- 供应商列表
- 供应商详情
- 数据采集配置
- 风险评估展示

Week 8: Phase 1 集成测试
- 前后端联调
- E2E 测试
- Demo 版本发布
        """,
        "metadata": {"source": "开发计划", "category": "项目管理"},
    },
]


async def main():
    """主函数"""
    print("=" * 60)
    print("鎏灏 AI-OS RAG 系统演示")
    print("=" * 60)
    print()

    # 1. 初始化 Ollama Provider
    print("[1/5] 初始化 Ollama Provider...")
    ollama_config = ProviderConfig(
        provider=ProviderType.OLLAMA,
        api_key_name="",
        enabled=True,
        base_url="http://localhost:11434",
        metadata={"default_model": "qwen2.5:7b"},
    )
    ollama_provider = OllamaProvider(ollama_config)
    print("✓ Ollama Provider 已初始化")
    print()

    # 2. 初始化 Embedding Provider
    print("[2/5] 初始化 Embedding Provider...")
    # 使用 ChromaDB 默认 Embedding (轻量快速)
    embedding_provider = create_embedding_provider("chroma_default")
    print("✓ 使用 ChromaDB Default Embedding (384-dim)")
    print()

    # 3. 初始化 Vector Store
    print("[3/5] 初始化 Vector Store...")
    vector_store = ChromaVectorStore(
        collection_name="rag_demo", persist_directory="./data/chroma"
    )
    print("✓ ChromaDB Vector Store 已初始化")
    print()

    # 4. 初始化 RAG System
    print("[4/5] 初始化 RAG System...")
    rag_system = RAGSystem(
        llm_provider=ollama_provider,
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        retrieval_top_k=3,
        chunk_size=400,  # 较小的块，便于精确检索
        chunk_overlap=50,
    )
    print("✓ RAG System 已初始化")
    print()

    # 5. 添加文档到知识库
    print("[5/5] 添加示例文档到知识库...")
    for i, doc in enumerate(SAMPLE_DOCUMENTS, 1):
        doc_id = await rag_system.add_document(
            text=doc["text"], metadata=doc["metadata"], document_id=f"doc_{i}"
        )
        print(f"  ✓ 文档 {i}/{len(SAMPLE_DOCUMENTS)}: {doc['metadata']['source']}")

    stats = await rag_system.get_stats()
    print(f"\n知识库统计：")
    print(f"  - 文档数量: {stats['total_documents']} 个块")
    print(f"  - Embedding: {stats['embedding_provider']}")
    print(f"  - Vector Store: {stats['vector_store_type']}")
    print()

    # 开始问答演示
    print("=" * 60)
    print("开始问答演示")
    print("=" * 60)
    print()

    questions = [
        "鎏灏 AI-OS 是什么？有哪些核心特性？",
        "AI 员工管理系统有哪些功能？",
        "Week 4 Day 4 的任务是什么？",
        "供应商风险评估有哪些维度？各占多少权重？",
    ]

    for i, question in enumerate(questions, 1):
        print(f"问题 {i}: {question}")
        print("-" * 60)

        # 查询（带检索结果）
        answer, results = await rag_system.generate_with_context(
            query=question, top_k=3, temperature=0.7
        )

        print(f"回答:\n{answer}\n")

        print("来源文档:")
        for j, result in enumerate(results, 1):
            source = result.document.metadata.get("source", "未知")
            category = result.document.metadata.get("category", "未知")
            score = int(result.score * 100)
            print(f"  [{j}] {source} ({category}) - 相关度: {score}%")

        print()
        print("=" * 60)
        print()

        # 避免请求过快
        await asyncio.sleep(1)

    print("演示完成！")
    print()
    print("提示：")
    print("- 如需清空知识库：await rag_system.clear_knowledge_base()")
    print("- 如需继续添加文档：await rag_system.add_document(...)")
    print("- 如需调整检索数量：修改 retrieval_top_k 参数")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n演示已中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
