#!/usr/bin/env python
"""行动模块完整测试 Demo"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.action import (
    ActionManager, get_action_manager,
    Action, ActionType, ActionResult, ExecutionContext,
    OutputType, ToolCall
)
from loguru import logger


async def demo_action_manager():
    """测试 1: 行动管理器"""
    print("\n" + "=" * 60)
    print("测试 1: 行动管理器初始化")
    print("=" * 60)

    manager = get_action_manager()

    # 注册内置工具
    manager.register_builtin_tools()

    print(f"✅ 已注册工具: {manager.list_tools()}")
    print(f"\n📋 工具描述:\n{manager.get_tools_description()}")

    return manager


async def demo_tool_execution(manager: ActionManager):
    """测试 2: 工具执行"""
    print("\n" + "=" * 60)
    print("测试 2: 工具执行")
    print("=" * 60)

    # 测试 1: 获取当前时间
    print("\n--- 测试 2.1: 获取当前时间 ---")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_current_time",
        tool_input={"timezone": "Asia/Shanghai"},
        session_id="test-001"
    )
    print(f"结果: {result.result}")
    print(f"耗时: {result.execution_time_ms:.2f}ms")

    # 测试 2: 知识库搜索
    print("\n--- 测试 2.2: 知识库搜索 ---")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="search_knowledge",
        tool_input={"query": "向量数据库", "top_k": 2},
        session_id="test-002"
    )
    print(f"结果预览: {result.result[:300]}...")

    # 测试 3: 知识库统计
    print("\n--- 测试 2.3: 知识库统计 ---")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_knowledge_stats",
        tool_input={},
        session_id="test-003"
    )
    print(f"结果:\n{result.result}")


async def demo_output_generation(manager: ActionManager):
    """测试 3: 输出生成"""
    print("\n" + "=" * 60)
    print("测试 3: 输出生成")
    print("=" * 60)

    # 模拟动作执行结果
    action_results = []

    # 模拟时间查询结果
    action_results.append(
        ActionResult(
            action=Action(
                type=ActionType.TOOL_CALL,
                tool_call=ToolCall(name="get_current_time", input={"timezone": "Asia/Shanghai"}),
                reasoning="获取当前时间"
            ),
            success=True,
            result="2026-05-03 14:30:00",
            execution_time_ms=150.0
        )
    )

    # 模拟知识搜索
    action_results.append(
        ActionResult(
            action=Action(
                type=ActionType.TOOL_CALL,
                tool_call=ToolCall(name="search_knowledge", input={"query": "CPU告警", "top_k": 2}),
                reasoning="搜索CPU告警相关知识"
            ),
            success=True,
            result="找到2条相关知识...\n【结果1】CPU使用率过高排查方法...\n【结果2】告警处理最佳实践...",
            execution_time_ms=200.0
        )
    )

    print(f"模拟了 {len(action_results)} 个动作执行结果")

    # 生成输出
    print("\n--- 生成最终输出 ---")
    output = await manager.generate_output(
        user_input="帮我分析CPU告警问题",
        action_results=action_results,
        output_type=OutputType.MARKDOWN,
        session_id="test-output"
    )

    print(f"\n📝 输出类型: {output.type.value}")
    print(f"📝 输出内容:\n{output.content[:500]}..." if len(output.content) > 500 else f"📝 输出内容:\n{output.content}")
    print(f"\n📊 元数据: {output.metadata}")


async def demo_stream_output(manager: ActionManager):
    """测试 4: 流式输出"""
    print("\n" + "=" * 60)
    print("测试 4: 流式输出")
    print("=" * 60)

    action_results = [
        ActionResult(
            action=Action(
                type=ActionType.TOOL_CALL,
                tool_call=ToolCall(name="search_knowledge", input={"query": "什么是向量数据库", "top_k": 1}),
                reasoning="搜索向量数据库定义"
            ),
            success=True,
            result="向量数据库是一种专门存储和检索向量数据的数据库系统，常用于 RAG、推荐系统等场景。",
            execution_time_ms=100.0
        )
    ]

    print("\n🤖 流式响应: ", end="", flush=True)

    async for chunk in manager.generate_output_stream(
            user_input="什么是向量数据库？",
            action_results=action_results,
            session_id="test-stream"
    ):
        print(chunk, end="", flush=True)

    print("\n\n✅ 流式输出完成")


async def demo_batch_actions(manager: ActionManager):
    """测试 5: 批量动作执行"""
    print("\n" + "=" * 60)
    print("测试 5: 批量动作执行")
    print("=" * 60)

    # 构建动作列表
    actions = [
        Action(
            type=ActionType.TOOL_CALL,
            tool_call=ToolCall(name="get_current_time", input={"timezone": "Asia/Shanghai"}),
            reasoning="获取当前时间"
        ),
        Action(
            type=ActionType.TOOL_CALL,
            tool_call=ToolCall(name="get_knowledge_stats", input={}),
            reasoning="获取知识库统计"
        ),
        Action(
            type=ActionType.DIRECT_OUTPUT,
            content="所有操作系统检查完成",
            reasoning="完成状态报告"
        )
    ]

    # 创建执行上下文
    context = ExecutionContext(
        session_id="test-batch",
        user_input="获取系统信息并报告状态",
        current_step="批量执行",
        available_tools=[
            {"name": "get_current_time", "description": "获取当前时间"},
            {"name": "get_knowledge_stats", "description": "获取知识库统计"}
        ]
    )

    print(f"执行 {len(actions)} 个动作...")

    results = await manager.execute_actions(actions, context, session_id="test-batch")

    print("\n📊 执行结果:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.success else "❌"
        print(f"  {i}. {status} {result.action.reasoning}")
        print(f"     耗时: {result.execution_time_ms:.2f}ms")
        if result.result:
            result_preview = result.result[:100] + "..." if len(result.result) > 100 else result.result
            print(f"     结果: {result_preview}")
        print()

    # 生成合并报告
    output = await manager.generate_output(
        user_input="获取系统信息并报告状态",
        action_results=results,
        output_type=OutputType.MARKDOWN,
        session_id="test-batch"
    )

    print(f"\n📝 合并报告:\n{output.content}")


async def demo_error_handling(manager: ActionManager):
    """测试 6: 错误处理"""
    print("\n" + "=" * 60)
    print("测试 6: 错误处理")
    print("=" * 60)

    print("\n--- 测试 6.1: 不存在的工具 ---")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="non_existent_tool",
        tool_input={},
        session_id="test-error-001"
    )
    print(f"结果: {result.result}")
    print(f"成功: {result.success}")

    print("\n--- 测试 6.2: 工具调用异常（参数错误） ---")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="search_knowledge",
        tool_input={"top_k": "invalid"},  # 错误参数类型
        session_id="test-error-002"
    )
    print(f"结果: {result.result}")
    print(f"成功: {result.success}")


async def demo_complete_workflow(manager: ActionManager):
    """测试 7: 完整工作流"""
    print("\n" + "=" * 60)
    print("测试 7: 完整工作流")
    print("=" * 60)

    user_input = "请帮我分析系统健康状态"
    print(f"\n📝 用户: {user_input}")
    print("⚙️ 开始执行...")

    # 步骤 1: 获取当前时间
    print("\n1️⃣ 获取当前时间...")
    time_result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_current_time",
        tool_input={},
        session_id="test-workflow"
    )
    print(f"   ✅ 当前时间: {time_result.result}")

    # 步骤 2: 获取知识库统计
    print("\n2️⃣ 检查知识库状态...")
    stats_result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_knowledge_stats",
        tool_input={},
        session_id="test-workflow"
    )
    print(f"   ✅ {stats_result.result.split(chr(10))[0]}")

    # 步骤 3: 搜索相关知识
    print("\n3️⃣ 检索健康分析知识...")
    knowledge_result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="search_knowledge",
        tool_input={"query": "系统健康检查", "top_k": 2},
        session_id="test-workflow"
    )
    print(f"   ✅ 找到相关知识")

    # 步骤 4: 生成最终报告
    print("\n4️⃣ 生成最终报告...")
    all_results = [time_result, stats_result, knowledge_result]

    output = await manager.generate_output(
        user_input=user_input,
        action_results=all_results,
        output_type=OutputType.MARKDOWN,
        session_id="test-workflow"
    )

    print(f"\n📝 最终报告:\n{'-' * 40}")
    print(output.content)
    print(f"{'-' * 40}")


async def main():
    """主函数"""
    print("\n" + "🎯" * 35)
    print("  行动模块完整测试套件")
    print("🎯" * 35)

    # 测试 1: 初始化
    manager = await demo_action_manager()

    # 测试 2: 工具执行
    await demo_tool_execution(manager)

    # 测试 3: 输出生成
    await demo_output_generation(manager)

    # 测试 4: 流式输出
    await demo_stream_output(manager)

    # 测试 5: 批量动作
    await demo_batch_actions(manager)

    # 测试 6: 错误处理
    await demo_error_handling(manager)

    # 测试 7: 完整工作流
    await demo_complete_workflow(manager)

    print("\n" + "✅" * 35)
    print("  所有测试完成！")
    print("✅" * 35)
    print()

    # 打印使用说明
    print("📖 行动模块使用说明")
    print("-" * 40)
    print("1. 获取行动管理器:")
    print("   from app.action import get_action_manager")
    print("   manager = get_action_manager()")
    print()
    print("2. 注册工具:")
    print("   manager.register_builtin_tools()")
    print("   # 或")
    print("   manager.register_tool(custom_tool)")
    print()
    print("3. 执行工具调用:")
    print("   result = await manager.run_single_action(")
    print("       action_type=ActionType.TOOL_CALL,")
    print("       tool_name='get_current_time',")
    print("       tool_input={}")
    print("   )")
    print()
    print("4. 生成输出:")
    print("   output = await manager.generate_output(")
    print("       user_input=user_input,")
    print("       action_results=results,")
    print("       output_type=OutputType.MARKDOWN")
    print("   )")
    print()
    print("5. 流式输出:")
    print("   async for chunk in manager.generate_output_stream(...):")
    print("       print(chunk, end='')")

if __name__ == "__main__":
    asyncio.run(main())