#!/usr/bin/env python
"""大脑模块完整测试 Demo - 使用行动模块的工具"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.brain import BrainManager, get_brain_manager
from app.action import get_action_manager
from loguru import logger


async def demo_simple():
    """测试 1: 简单问答（无需工具）"""
    print("\n" + "=" * 60)
    print("测试 1: 简单问答（无需工具）")
    print("=" * 60)

    # 获取大脑管理器
    brain = get_brain_manager()

    # 测试问题
    question = "你好，请简单介绍一下你自己"
    print(f"\n📝 用户: {question}")
    print("-" * 40)

    try:
        response = await brain.think(
            user_input=question,
            session_id="test-session-1",
            perception_context={}
        )
        print(f"🤖 大脑回答:\n{response.answer}")
        print(f"\n📊 执行统计: 共执行了 {len(response.execution_history)} 个步骤")
        print(f"🎯 响应长度: {len(response.answer)} 字符")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ 错误: {e}")


async def demo_with_context():
    """测试 2: 带上下文信息的问答"""
    print("\n" + "=" * 60)
    print("测试 2: 带上下文信息的问答")
    print("=" * 60)

    brain = get_brain_manager()

    # 模拟感知上下文
    perception_context = {
        "environment": {
            "current_time": "2026-05-03 14:30:00",
            "system_status": {
                "cpu_percent": 45.5,
                "memory_percent": 62.3
            }
        },
        "short_term_memory": [],
        "long_term_memory": []
    }

    question = "基于当前的系统状态，请分析系统是否健康"
    print(f"\n📝 用户: {question}")
    print(f"📊 上下文: CPU={perception_context['environment']['system_status']['cpu_percent']}%, "
          f"内存={perception_context['environment']['system_status']['memory_percent']}%")
    print("-" * 40)

    try:
        response = await brain.think(
            user_input=question,
            session_id="test-session-2",
            perception_context=perception_context
        )
        print(f"🤖 大脑回答:\n{response.answer}")
        print(f"\n📊 执行统计: 共执行了 {len(response.execution_history)} 个步骤")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ 错误: {e}")


async def demo_with_perception():
    """测试 3: 完整感知 + 大脑思考"""
    print("\n" + "=" * 60)
    print("测试 3: 完整感知 + 大脑思考")
    print("=" * 60)

    try:
        from app.perception import PerceptionManager

        perception = PerceptionManager()
        brain = get_brain_manager()

        user_input = "帮我分析一下当前系统状态"

        print(f"\n📝 用户: {user_input}")
        print("🔍 执行感知模块...")

        # 执行感知
        perception_result = await perception.perceive(
            input_text=user_input,
            session_id="test-session-3",
            include_long_term=False  # 暂不检索长期记忆
        )

        print(f"   感知摘要: {perception_result.summary[:100]}")
        print(f"   环境时间: {perception_result.environment_context.current_time}")
        cpu = perception_result.environment_context.system_status.get('cpu_percent', 'N/A')
        mem = perception_result.environment_context.system_status.get('memory_percent', 'N/A')
        print(f"   系统状态: CPU {cpu}%, 内存 {mem}%")

        print("\n🧠 大脑思考中...")

        # 大脑思考
        response = await brain.think(
            user_input=user_input,
            session_id="test-session-3",
            perception_context=perception_result.to_dict()
        )

        print(f"\n🤖 大脑回答:\n{response.answer}")
        print(f"\n📊 执行统计: 共执行了 {len(response.execution_history)} 个步骤")

        # 打印执行历史（如果有）
        if response.execution_history:
            print(f"\n📋 执行历史:")
            for i, step in enumerate(response.execution_history, 1):
                status = "✓" if step.success else "✗"
                print(f"   {i}. [{status}] {step.step[:50]}...")
                if step.result:
                    result_preview = step.result[:100]
                    print(f"      结果: {result_preview}...")

    except ImportError as e:
        print(f"⚠️ 感知模块导入失败: {e}")
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ 错误: {e}")


async def demo_stream():
    """测试 4: 流式输出"""
    print("\n" + "=" * 60)
    print("测试 4: 流式输出")
    print("=" * 60)

    brain = get_brain_manager()

    question = "请简要介绍一下什么是 RAG（检索增强生成）技术"
    print(f"\n📝 用户: {question}")
    print("🤖 大脑流式响应: ", end="", flush=True)
    print()

    try:
        event_count = 0
        full_response = []

        async for event in brain.think_stream(
                user_input=question,
                session_id="test-stream-session",
                perception_context={}
        ):
            event_count += 1
            event_type = event.get("type", "unknown")

            if event_type == "plan":
                steps = event.get("steps", [])
                print(f"\n[计划] 共 {len(steps)} 个步骤")
                for i, step in enumerate(steps, 1):
                    print(f"  {i}. {step}")

            elif event_type == "step_start":
                print(f"\n[执行] {event.get('step', '')[:60]}...")

            elif event_type == "tool_call":
                print(f"\n[工具] 调用 {event.get('tool', 'unknown')}")

            elif event_type == "step_complete":
                if event.get("success"):
                    print(f"\n[完成] ✓ 步骤完成，剩余 {event.get('remaining_steps', 0)} 步")
                else:
                    print(f"\n[完成] ✗ 步骤失败")

            elif event_type == "response_chunk":
                chunk = event.get("data", "")
                full_response.append(chunk)
                print(chunk, end="", flush=True)

            elif event_type == "status":
                print(f"\n[状态] {event.get('message', '')}")

            elif event_type == "complete":
                print(f"\n\n✅ 完成! 共收到 {event_count} 个事件")
                print(f"📊 响应长度: {len(''.join(full_response))} 字符")

        print()

    except Exception as e:
        logger.error(f"流式测试失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"❌ 错误: {e}")


async def demo_tool_integration():
    """测试 5: 工具集成 - 使用行动模块的工具"""
    print("\n" + "=" * 60)
    print("测试 5: 工具集成（使用行动模块）")
    print("=" * 60)

    brain = get_brain_manager()

    # 注册内置工具（通过行动模块）
    brain.register_builtin_tools()

    print(f"🔧 已注册工具: {brain.list_tools()}")

    # 先查看知识库状态
    print("\n" + "-" * 40)
    print("📊 知识库状态")
    try:
        # 通过行动管理器获取知识库统计
        action_manager = get_action_manager()
        stats_result = await action_manager.execute_tool_call(
            tool_name="get_knowledge_stats",
            tool_input={},
            session_id="test-stats"
        )
        print(stats_result)
    except Exception as e:
        print(f"⚠️ 无法获取知识库状态: {e}")

    # 测试 1: 获取当前时间
    print("\n" + "-" * 40)
    print("测试 5.1: 获取当前时间")
    question = "现在几点了？"
    print(f"📝 用户: {question}")

    try:
        response = await brain.think(
            user_input=question,
            session_id="test-tools-session-1",
            perception_context={},
            available_tools=[
                {"name": "get_current_time", "description": "获取当前时间，无需参数，返回格式化的时间字符串"},
                {"name": "search_knowledge", "description": "从知识库搜索信息，参数 query: 搜索查询词, top_k: 返回数量"},
                {"name": "get_knowledge_stats", "description": "获取知识库统计信息"}
            ]
        )

        print(f"🤖 大脑回答:\n{response.answer}")

        # 显示工具调用详情
        for step in response.execution_history:
            if step.action.type.value == "tool_call":
                print(f"\n🔧 工具调用详情:")
                print(f"   工具: {step.action.tool_name}")
                print(f"   参数: {step.action.tool_input}")
                print(f"   结果: {step.result[:200]}...")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 错误: {e}")

    # 测试 2: 知识库搜索
    print("\n" + "-" * 40)
    print("测试 5.2: 知识库搜索")
    question2 = "如何排查 CPU 告警问题？"
    print(f"📝 用户: {question2}")

    try:
        response2 = await brain.think(
            user_input=question2,
            session_id="test-tools-session-2",
            perception_context={},
            available_tools=[
                {"name": "get_current_time", "description": "获取当前时间"},
                {"name": "search_knowledge", "description": "从知识库搜索信息，参数 query: 搜索查询词, top_k: 返回数量"},
                {"name": "search_knowledge_with_filter", "description": "按分类搜索知识，参数 query, category, top_k"},
                {"name": "get_knowledge_stats", "description": "获取知识库统计信息"}
            ]
        )

        print(f"🤖 大脑回答:\n{response2.answer}")

        # 显示工具调用详情
        print(f"\n📊 执行统计: 共执行了 {len(response2.execution_history)} 个步骤")
        for step in response2.execution_history:
            if step.action.type.value == "tool_call":
                print(f"\n🔧 工具调用详情:")
                print(f"   工具: {step.action.tool_name}")
                print(f"   参数: {step.action.tool_input}")
                result_preview = step.result[:200] if step.result else "无结果"
                print(f"   结果预览: {result_preview}...")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 错误: {e}")

    # 测试 3: 多轮对话
    print("\n" + "-" * 40)
    print("测试 5.3: 多轮对话")
    follow_up = "能给我更具体的排查步骤吗？"
    print(f"📝 用户: {follow_up}")

    try:
        response3 = await brain.think(
            user_input=follow_up,
            session_id="test-tools-session-2",  # 使用相同的 session_id
            perception_context={},
            available_tools=[
                {"name": "get_current_time", "description": "获取当前时间"},
                {"name": "search_knowledge", "description": "从知识库搜索信息"}
            ]
        )

        print(f"🤖 大脑回答:\n{response3.answer}")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"❌ 错误: {e}")


async def demo_add_knowledge():
    """测试 6: 添加知识到知识库（通过行动模块）"""
    print("\n" + "=" * 60)
    print("测试 6: 添加知识到知识库（通过行动模块）")
    print("=" * 60)

    action_manager = get_action_manager()

    # 确保内置工具已注册
    action_manager.register_builtin_tools()

    # 测试添加新知识
    test_knowledge = [
        {
            "content": "Docker 容器常用命令：docker ps 查看运行中的容器，docker logs 查看容器日志，docker exec 进入容器执行命令。",
            "category": "docker",
            "source": "test_demo"
        },
        {
            "content": "Kubernetes 故障排查：使用 kubectl describe pod 查看 Pod 详情，kubectl logs 查看日志，kubectl exec 进入容器调试。",
            "category": "kubernetes",
            "source": "test_demo"
        },
        {
            "content": "Python 性能优化：使用 cProfile 进行性能分析，使用 multiprocessing 实现并行计算，使用 asyncio 提升 IO 密集型任务效率。",
            "category": "python",
            "source": "test_demo"
        }
    ]

    print("\n📚 添加测试知识到知识库:")

    for knowledge in test_knowledge:
        print(f"\n  内容: {knowledge['content'][:50]}...")
        print(f"  分类: {knowledge['category']}")

        try:
            result = await action_manager.execute_tool_call(
                tool_name="add_to_knowledge",
                tool_input={
                    "content": knowledge["content"],
                    "category": knowledge["category"],
                    "source": knowledge["source"]
                },
                session_id="test-add"
            )
            print(f"  结果: {result}")
        except Exception as e:
            print(f"  ❌ 添加失败: {e}")

    # 再次查看知识库状态
    print("\n" + "-" * 40)
    print("📊 更新后的知识库状态:")
    try:
        stats = await action_manager.execute_tool_call(
            tool_name="get_knowledge_stats",
            tool_input={},
            session_id="test-stats"
        )
        print(stats)
    except Exception as e:
        print(f"⚠️ 无法获取知识库状态: {e}")


async def demo_hybrid_search():
    """测试 7: 混合搜索（向量 + 分类过滤）- 通过行动模块"""
    print("\n" + "=" * 60)
    print("测试 7: 混合搜索（通过行动模块）")
    print("=" * 60)

    action_manager = get_action_manager()
    action_manager.register_builtin_tools()

    # 测试不同分类的搜索
    test_queries = [
        ("Docker", None),
        ("性能优化", "python"),
        ("容器", "docker"),
        ("Kubernetes 调试", "kubernetes"),
    ]

    for query, category in test_queries:
        print(f"\n📝 搜索: '{query}'" + (f" (分类: {category})" if category else ""))

        try:
            if category:
                result = await action_manager.execute_tool_call(
                    tool_name="search_knowledge_with_filter",
                    tool_input={
                        "query": query,
                        "category": category,
                        "top_k": 2
                    },
                    session_id="test-search"
                )
            else:
                result = await action_manager.execute_tool_call(
                    tool_name="search_knowledge",
                    tool_input={
                        "query": query,
                        "top_k": 2
                    },
                    session_id="test-search"
                )

            # 只显示前300字符
            preview = result[:300] + "..." if len(result) > 300 else result
            print(f"结果:\n{preview}")

        except Exception as e:
            print(f"❌ 搜索失败: {e}")


async def main():
    """主函数"""
    print("\n" + "🧠" * 35)
    print("  大脑模块完整测试套件（使用行动模块）")
    print("🧠" * 35)

    # 运行所有测试
    await demo_simple()
    await demo_with_context()
    await demo_with_perception()
    await demo_stream()
    await demo_tool_integration()
    await demo_add_knowledge()
    await demo_hybrid_search()

    print("\n" + "✅" * 35)
    print("  所有测试完成！")
    print("✅" * 35)
    print()


if __name__ == "__main__":
    asyncio.run(main())