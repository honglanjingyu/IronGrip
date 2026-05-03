# examples/memory/demo_long_term_simple.py
# !/usr/bin/env python
"""长期记忆单独测试 - 仅测试检索和添加功能"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory.long_term_memory import LongTermMemory
from app.memory.models import LongTermConfig
from app.memory.config import memory_config


async def demo_long_term():
    print("\n" + "=" * 50)
    print("长期记忆测试")
    print("=" * 50)

    print(f"\n配置信息:")
    print(f"  Milvus地址: {memory_config.MILVUS_HOST}:{memory_config.MILVUS_PORT}")
    print(f"  Embedding类型: {memory_config.EMBEDDING_TYPE}")
    print(f"  Top-K: {memory_config.SIMILARITY_TOP_K}")

    config = LongTermConfig(
        top_k=3,
        similarity_threshold=0.3
    )

    print("\n初始化 LongTermMemory...")
    try:
        long_memory = LongTermMemory(config=config)
    except Exception as e:
        print(f"初始化失败: {e}")
        print("\n提示：长期记忆需要 Milvus 和 Embedding 服务")
        print("  1. 请确保 Milvus 服务已启动")
        print("  2. 请确保已配置 LLM_API_KEY")
        return False

    print("\n检查状态:")
    stats = long_memory.get_stats()
    print(f"  可用: {stats.get('available', False)}")
    print(f"  文档数: {stats.get('num_entities', 0)}")

    # 添加测试知识（如果知识库为空）
    if stats.get('num_entities', 0) == 0:
        print("\n知识库为空，添加测试知识...")
        success = await long_memory.add_knowledge(
            content="CPU告警排查方法：当CPU使用率超过80%时，首先使用top命令查看CPU占用最高的进程。",
            metadata={"category": "troubleshooting", "source": "test"}
        )
        if success:
            print("  测试知识添加成功")
        else:
            print("  添加测试知识失败（可能 Milvus 未连接）")

        # 再添加一条
        await long_memory.add_knowledge(
            content="RAG技术介绍：检索增强生成，结合检索和生成技术，可以有效减少幻觉。",
            metadata={"category": "ai", "source": "test"}
        )

    # 检索测试
    print("\n检索测试:")
    test_queries = ["CPU 告警", "RAG"]

    for query in test_queries:
        print(f"\n  查询: {query}")
        try:
            results = await long_memory.retrieve(query, top_k=2, enable_rerank=False)
            if results:
                print(f"    找到 {len(results)} 条结果:")
                for i, item in enumerate(results, 1):
                    preview = item.content[:80] + "..." if len(item.content) > 80 else item.content
                    print(f"      {i}. [相似度: {item.score:.4f}] {preview}")
            else:
                print(f"    未找到相关结果")
        except Exception as e:
            print(f"    检索失败: {e}")

    print("\n" + "=" * 50)
    return True


async def main():
    result = await demo_long_term()
    if result:
        print("\n✅ 测试完成")
    else:
        print("\n⚠️ 测试完成（部分功能可能因配置问题不可用）")


if __name__ == "__main__":
    asyncio.run(main())