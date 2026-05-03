#!/usr/bin/env python
"""测试 Milvus 知识库集成（通过行动模块）"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.action import get_action_manager
from loguru import logger


async def demo_milvus_knowledge():
    print("\n" + "=" * 60)
    print("测试 Milvus 知识库集成（通过行动模块）")
    print("=" * 60)

    # 获取行动管理器
    action_manager = get_action_manager()
    action_manager.register_builtin_tools()

    # 1. 查看知识库状态
    print("\n1. 知识库状态:")
    try:
        stats = await action_manager.execute_tool_call(
            tool_name="get_knowledge_stats",
            tool_input={},
            session_id="test-stats"
        )
        print(stats)
    except Exception as e:
        print(f"⚠️ 无法获取知识库状态: {e}")

    # 2. 添加测试知识
    print("\n2. 添加测试知识:")
    try:
        result = await action_manager.execute_tool_call(
            tool_name="add_to_knowledge",
            tool_input={
                "content": "Redis 缓存使用指南：Redis 是一种内存数据库，常用于缓存、会话存储、消息队列等场景。最大内存限制默认无限制，建议设置 maxmemory 参数。",
                "category": "database",
                "source": "test"
            },
            session_id="test-add"
        )
        print(result)
    except Exception as e:
        print(f"❌ 添加失败: {e}")

    # 3. 搜索知识
    print("\n3. 搜索 'Redis 缓存':")
    try:
        result = await action_manager.execute_tool_call(
            tool_name="search_knowledge",
            tool_input={
                "query": "Redis 缓存",
                "top_k": 3
            },
            session_id="test-search"
        )
        print(result)
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

    # 4. 分类搜索
    print("\n4. 分类搜索 (数据库类):")
    try:
        result = await action_manager.execute_tool_call(
            tool_name="search_knowledge_with_filter",
            tool_input={
                "query": "使用指南",
                "category": "database",
                "top_k": 3
            },
            session_id="test-search"
        )
        print(result)
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

    # 5. 搜索故障排查
    print("\n5. 搜索 'CPU 告警':")
    try:
        result = await action_manager.execute_tool_call(
            tool_name="search_knowledge",
            tool_input={
                "query": "CPU 告警如何处理",
                "top_k": 3
            },
            session_id="test-search"
        )
        print(result)
    except Exception as e:
        print(f"❌ 搜索失败: {e}")


async def main():
    await demo_milvus_knowledge()


if __name__ == "__main__":
    asyncio.run(main())