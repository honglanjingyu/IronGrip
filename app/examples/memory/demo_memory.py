# examples/memory/demo_memory.py
# !/usr/bin/env python
"""记忆模块完整测试 Demo - 适配你的配置"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.memory import (
    MemoryManager,
    ShortTermConfig, WorkingMemoryConfig, LongTermConfig,
)
from app.memory.config import memory_config
from loguru import logger


def print_section(title: str, char: str = "=", width: int = 60):
    """打印分节标题"""
    print("\n" + char * width)
    print(f" {title}")
    print(char * width)


def print_config():
    """打印当前配置"""
    print_section("当前配置")
    print(f"  Embedding 类型: {memory_config.EMBEDDING_TYPE}")
    print(f"  Embedding 模型: {memory_config.EMBEDDING_MODEL}")
    print(f"  向量存储类型: {memory_config.VECTOR_STORE_TYPE}")
    print(f"  Milvus 地址: {memory_config.MILVUS_HOST}:{memory_config.MILVUS_PORT}")
    print(f"  相似度阈值: {memory_config.SIMILARITY_THRESHOLD}")
    print(f"  Top-K: {memory_config.SIMILARITY_TOP_K}")
    print(f"  重排序类型: {memory_config.RERANK_TYPE}")
    print(f"  重排序模型: {memory_config.RERANK_MODEL}")


async def demo_short_term_memory():
    """测试 1: 短期记忆"""
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
    """测试 2: 工作记忆"""
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


async def demo_long_term_memory():
    """测试 3: 长期记忆（向量知识库）"""
    print_section("测试 3: 长期记忆（向量知识库）")

    config = LongTermConfig(
        top_k=memory_config.SIMILARITY_TOP_K,
        similarity_threshold=memory_config.SIMILARITY_THRESHOLD
    )

    memory = MemoryManager(long_term_config=config)

    print(f"\n检查长期记忆状态:")
    stats = memory.long_term.get_stats()
    print(f"  可用: {stats.get('available', False)}")
    if stats.get('available'):
        print(f"  集合: {stats.get('collection_name', 'unknown')}")
        print(f"  文档数: {stats.get('num_entities', 0)}")

    # 添加测试知识
    print("\n添加测试知识到长期记忆...")

    test_knowledge = [
        {
            "content": "CPU告警排查方法：当CPU使用率超过80%时，首先使用top命令查看CPU占用最高的进程，然后分析该进程的日志，检查是否存在死循环或资源泄露。",
            "metadata": {"category": "troubleshooting", "source": "test_demo", "topic": "cpu_alert"}
        },
        {
            "content": "数据同步服务常见问题：同步延迟通常由网络问题、源库负载过高或目标库写入瓶颈引起。解决方案包括优化查询、增加并发、使用批量写入。",
            "metadata": {"category": "data-sync", "source": "test_demo", "topic": "sync_delay"}
        },
        {
            "content": "RAG（检索增强生成）是一种结合信息检索和语言生成的技术。它先从知识库中检索相关信息，然后基于检索结果生成回答，可以有效减少幻觉问题。",
            "metadata": {"category": "ai_tech", "source": "test_demo", "topic": "rag"}
        },
        {
            "content": "Milvus向量数据库使用指南：Milvus是一款开源向量数据库，支持百亿级向量检索。主要概念包括Collection（集合）、Partition（分区）、Index（索引）等。",
            "metadata": {"category": "database", "source": "test_demo", "topic": "milvus"}
        },
    ]

    for knowledge in test_knowledge:
        success = await memory.add_to_long_term(
            content=knowledge["content"],
            metadata=knowledge["metadata"]
        )
        print(f"  {'成功' if success else '失败'} {knowledge['metadata']['topic']}")

    # 检索测试
    print(f"\n检索测试:")

    test_queries = [
        "CPU 告警如何排查",
        "数据同步延迟怎么办",
        "什么是 RAG 技术",
        "Milvus 是什么",
    ]

    for query in test_queries:
        print(f"\n  查询: {query}")
        results = await memory.retrieve_long_term(query, top_k=2)

        if results:
            for i, item in enumerate(results, 1):
                print(f"    {i}. [相似度: {item.score:.4f}] {item.content[:80]}...")
                print(f"       来源: {item.metadata.get('source', 'unknown')}")
        else:
            print(f"    未找到相关结果")

    return memory


async def demo_hybrid_retrieval():
    """测试 4: 混合检索和重排序"""
    print_section("测试 4: 混合检索和重排序")

    memory = MemoryManager()

    # 添加更多测试数据
    print("\n添加更多测试知识...")

    additional_knowledge = [
        "系统性能优化最佳实践：定期监控CPU、内存、磁盘使用率，设置合理的告警阈值，及时处理异常。",
        "Python性能优化技巧：使用cProfile进行性能分析，使用多进程处理CPU密集型任务，使用asyncio处理IO密集型任务。",
        "Docker容器故障排查：使用docker logs查看日志，docker exec进入容器调试，docker stats查看资源使用。",
        "Kubernetes问题排查：kubectl describe pod查看详情，kubectl logs查看日志，kubectl top查看资源使用。",
    ]

    for content in additional_knowledge:
        await memory.add_to_long_term(content, {"source": "performance_tips"})
        print(f"  已添加: {content[:40]}...")

    # 测试重排序效果
    print(f"\n检索测试（带重排序）:")

    query = "如何排查系统性能问题"
    print(f"\n  查询: {query}")

    results = await memory.retrieve_long_term(query, top_k=3, enable_rerank=True)

    if results:
        print(f"\n  检索结果（已重排序）:")
        for i, item in enumerate(results, 1):
            print(f"    {i}. [分数: {item.score:.4f}] {item.content[:100]}...")
    else:
        print(f"    未找到相关结果")

    return memory


async def demo_memory_manager_comprehensive():
    """测试 5: 记忆管理器综合测试"""
    print_section("测试 5: 记忆管理器综合测试")

    memory = MemoryManager()

    # 设置当前会话
    memory.set_session("comprehensive-test-session")
    print(f"\n会话ID: comprehensive-test-session")

    # 1. 添加对话到短期记忆
    print("\n步骤1: 添加对话...")
    memory.add_user_message("我的数据同步服务出现CPU告警")
    memory.add_assistant_message("收到，我来帮您分析CPU告警问题。请稍等，我正在获取监控数据。")
    memory.add_user_message("告警级别是critical，持续了15分钟")
    memory.add_assistant_message("了解，这是一个严重告警。让我查询一下相关日志和监控数据。")

    print(f"  短期记忆: {memory.short_term.get_size()} 条消息")

    # 2. 存储工作记忆
    print("\n步骤2: 存储工作记忆...")
    memory.set_working("alert_info", {
        "name": "HighCPUUsage",
        "severity": "critical",
        "duration": "15m",
        "service": "data-sync-service"
    })
    memory.set_working("investigation_step", "checking_logs")
    memory.set_working("findings", [
        "CPU使用率峰值达到92%",
        "异常进程为data-sync-worker",
        "日志中出现大量连接超时"
    ])

    print(f"  工作记忆: {len(memory.get_all_working())} 条")

    # 3. 检索长期记忆（如果可用）
    print("\n步骤3: 检索长期记忆...")
    if memory.long_term.is_available():
        results = await memory.retrieve_long_term("CPU告警排查方法", top_k=3)
        print(f"  检索到 {len(results)} 条相关知识")
        for item in results[:2]:
            print(f"    - {item.content[:60]}...")
    else:
        print("  长期记忆不可用（Milvus未连接或无数据）")

    # 4. 获取综合统计
    print(f"\n步骤4: 记忆统计")
    stats = memory.get_stats()
    print(f"  短期记忆: {stats.short_term_count} 条")
    print(f"  工作记忆: {stats.working_count} 条")
    print(f"  长期记忆: {stats.long_term_count} 条")
    print(f"  总计: {stats.total_count} 条")

    # 5. 获取综合上下文
    print(f"\n步骤5: 综合上下文（用于LLM）")
    context = memory.get_short_term_context()
    working_summary = memory.get_working_summary()

    print(f"  对话上下文:\n{context[:200]}...")
    print(f"\n  工作记忆摘要:\n{working_summary}")

    return memory


async def demo_clear_session():
    """测试 6: 清空会话"""
    print_section("测试 6: 清空会话")

    memory = MemoryManager()
    memory.set_session("test-clear-session")

    # 添加一些数据
    memory.add_user_message("测试消息1")
    memory.add_assistant_message("测试回复1")
    memory.set_working("test_key", "test_value")

    print(f"\n清空前:")
    print(f"  短期记忆: {memory.short_term.get_size()} 条")
    print(f"  工作记忆: {len(memory.get_all_working())} 条")

    # 清空会话
    memory.clear_session()

    print(f"\n清空后:")
    print(f"  短期记忆: {memory.short_term.get_size()} 条")
    print(f"  工作记忆: {len(memory.get_all_working())} 条")

    print(f"\n会话已清空")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  记忆模块完整测试套件")
    print("=" * 60)

    # 打印配置
    print_config()

    try:
        # 运行所有测试
        await demo_short_term_memory()
        await demo_working_memory()
        await demo_long_term_memory()
        await demo_hybrid_retrieval()
        await demo_memory_manager_comprehensive()
        await demo_clear_session()

        print("\n" + "=" * 60)
        print("  所有测试完成！")
        print("=" * 60)

        # 使用说明
        print("\n记忆模块使用说明")
        print("-" * 40)
        print("1. 获取记忆管理器:")
        print("   from app.memory import get_memory_manager")
        print("   memory = get_memory_manager()")
        print()
        print("2. 添加对话（短期记忆）:")
        print("   memory.add_user_message('用户问题')")
        print("   memory.add_assistant_message('助手回答')")
        print()
        print("3. 存储工作记忆:")
        print("   memory.set_working('key', value)")
        print("   value = memory.get_working('key')")
        print()
        print("4. 检索长期记忆:")
        print("   results = await memory.retrieve_long_term('查询文本')")
        print()
        print("5. 添加知识到长期记忆:")
        print("   await memory.add_to_long_term('知识内容', metadata={'category': 'tech'})")
        print()
        print("6. 清空会话:")
        print("   memory.clear_session()")

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)