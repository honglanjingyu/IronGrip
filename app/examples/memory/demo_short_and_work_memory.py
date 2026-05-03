# examples/memory/demo_memory_simple.py
#!/usr/bin/env python
"""记忆模块简单测试 - 只测试短期记忆和工作记忆，不依赖 Milvus"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory import (
    MemoryManager,
    ShortTermConfig, WorkingMemoryConfig,
)
from app.memory.config import memory_config


def print_section(title: str, char: str = "=", width: int = 60):
    print("\n" + char * width)
    print(f" {title}")
    print(char * width)


async def demo_short_term_memory():
    """测试短期记忆"""
    print_section("测试 1: 短期记忆（对话上下文）")

    config = ShortTermConfig(max_size=10)
    memory = MemoryManager(short_term_config=config)

    print("\n添加对话消息...")

    conversations = [
        ("你好，请问你能做什么？", "你好！我是AI助手，可以帮助你回答问题、搜索信息、分析数据等。"),
        ("能帮我查一下系统的CPU使用率吗？", "好的，让我查询一下系统监控数据。"),
        ("数据同步服务出现告警，请分析原因", "收到，正在分析数据同步服务的告警信息..."),
    ]

    for i, (user, assistant) in enumerate(conversations, 1):
        print(f"\n  第{i}轮对话:")
        print(f"    用户: {user}")
        print(f"    助手: {assistant[:50]}...")
        memory.add_conversation(user, assistant)

    print(f"\n短期记忆统计:")
    stats = memory.get_stats()
    print(f"  消息数量: {stats.short_term_count}")

    print(f"\n格式化的对话上下文:")
    context = memory.get_short_term_context()
    print(f"{context}")

    return memory


async def demo_working_memory():
    """测试工作记忆"""
    print_section("测试 2: 工作记忆（任务中间结果）")

    config = WorkingMemoryConfig(max_items=20, ttl_seconds=300)
    memory = MemoryManager(working_config=config)

    print("\n存储工作记忆...")

    memory.set_working("current_task", "分析CPU告警原因")
    memory.set_working("cpu_usage", 85.5)
    memory.set_working("memory_usage", 72.3)
    memory.set_working("affected_services", ["data-sync-service", "api-gateway"])
    memory.set_working("investigation_status", "analyzing_logs")

    print("  已存储5个工作记忆")

    print(f"\n获取工作记忆:")
    print(f"  current_task: {memory.get_working('current_task')}")
    print(f"  cpu_usage: {memory.get_working('cpu_usage')}%")
    print(f"  affected_services: {memory.get_working('affected_services')}")

    print(f"\n工作记忆摘要:")
    summary = memory.get_working_summary()
    print(f"{summary}")

    return memory


async def demo_clear_session():
    """测试清空会话"""
    print_section("测试 3: 清空会话")

    memory = MemoryManager()
    memory.set_session("test-clear-session")

    memory.add_user_message("测试消息1")
    memory.add_assistant_message("测试回复1")
    memory.set_working("test_key", "test_value")

    print(f"\n清空前:")
    print(f"  短期记忆: {memory.short_term.get_size()} 条")
    print(f"  工作记忆: {len(memory.get_all_working())} 条")

    memory.clear_session()

    print(f"\n清空后:")
    print(f"  短期记忆: {memory.short_term.get_size()} 条")
    print(f"  工作记忆: {len(memory.get_all_working())} 条")

    print(f"\n会话已清空")


async def main():
    print("\n" + "=" * 60)
    print("  记忆模块简单测试（不依赖 Milvus）")
    print("=" * 60)
    print(f"\n配置信息:")
    print(f"  Embedding 类型: {memory_config.EMBEDDING_TYPE}")
    print(f"  向量存储类型: {memory_config.VECTOR_STORE_TYPE}")

    try:
        await demo_short_term_memory()
        await demo_working_memory()
        await demo_clear_session()

        print("\n" + "=" * 60)
        print("  所有测试完成！")
        print("=" * 60)

        print("\n使用说明:")
        print("-" * 40)
        print("from app.memory import get_memory_manager")
        print("memory = get_memory_manager()")
        print("memory.add_user_message('用户问题')")
        print("memory.add_assistant_message('助手回答')")
        print("memory.set_working('key', value)")
        print("value = memory.get_working('key')")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)