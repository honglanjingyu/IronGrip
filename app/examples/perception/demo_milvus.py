#!/usr/bin/env python
"""简单测试 Milvus 连接和文档添加"""

import asyncio
from app.perception import MilvusVectorStore, PerceptionManager
from langchain_core.documents import Document


async def demo_simple():
    print("=" * 60)
    print("简单 Milvus 测试")
    print("=" * 60)

    # 1. 创建向量存储
    print("\n1. 创建 MilvusVectorStore...")
    try:
        vector_store = MilvusVectorStore()
        print("   ✅ 创建成功")
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        return

    # 2. 查看集合状态
    print("\n2. 查看集合状态...")
    stats = vector_store.get_collection_stats()
    print(f"   集合存在: {stats.get('exists', False)}")
    print(f"   文档数量: {stats.get('num_entities', 0)}")

    # 3. 添加测试文档
    print("\n3. 添加测试文档...")
    test_docs = [
        Document(
            page_content="这是第一个测试文档，用于验证 Milvus 存储功能。",
            metadata={"source": "test", "id": "test_001"}
        ),
        Document(
            page_content="这是第二个测试文档，包含关于向量数据库的知识。",
            metadata={"source": "test", "id": "test_002"}
        ),
    ]

    ids = vector_store.add_documents(test_docs)
    print(f"   ✅ 成功添加 {len(ids)} 个文档")

    # 4. 验证文档已添加
    print("\n4. 验证文档已添加...")
    stats = vector_store.get_collection_stats()
    print(f"   当前文档数量: {stats.get('num_entities', 0)}")

    # 5. 测试搜索
    print("\n5. 测试相似度搜索...")
    query = "向量数据库是什么？"
    results = vector_store.similarity_search(query, k=2)
    print(f"   查询: {query}")
    print(f"   找到 {len(results)} 个结果:")
    for i, doc in enumerate(results, 1):
        print(f"   {i}. {doc.page_content[:80]}...")

    print("\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(demo_simple())