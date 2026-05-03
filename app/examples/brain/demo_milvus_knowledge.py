#!/usr/bin/env python
"""测试 Milvus 知识库集成"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.builtin_tools import (
    search_knowledge,
    search_knowledge_with_filter,
    get_knowledge_stats,
    add_to_knowledge
)
from loguru import logger


async def demo_milvus_knowledge():
    print("\n" + "=" * 60)
    print("测试 Milvus 知识库集成")
    print("=" * 60)

    # 1. 查看知识库状态
    print("\n1. 知识库状态:")
    stats = await get_knowledge_stats.ainvoke({})
    print(stats)

    # 2. 添加测试知识
    print("\n2. 添加测试知识:")
    result = await add_to_knowledge.ainvoke({
        "content": "Redis 缓存使用指南：Redis 是一种内存数据库，常用于缓存、会话存储、消息队列等场景。最大内存限制默认无限制，建议设置 maxmemory 参数。",
        "category": "database",
        "source": "test"
    })
    print(result)

    # 3. 搜索知识
    print("\n3. 搜索 'Redis 缓存':")
    result = await search_knowledge.ainvoke({
        "query": "Redis 缓存",
        "top_k": 3
    })
    print(result)

    # 4. 分类搜索
    print("\n4. 分类搜索 (数据库类):")
    result = await search_knowledge_with_filter.ainvoke({
        "query": "使用指南",
        "category": "database",
        "top_k": 3
    })
    print(result)

    # 5. 搜索故障排查
    print("\n5. 搜索 'CPU 告警':")
    result = await search_knowledge.ainvoke({
        "query": "CPU 告警如何处理",
        "top_k": 3
    })
    print(result)


async def main():
    await demo_milvus_knowledge()


if __name__ == "__main__":
    asyncio.run(main())