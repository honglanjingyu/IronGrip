#!/usr/bin/env python
"""测试大脑模块 + 真实工具"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.brain import get_brain_manager
from app.tools.builtin_tools import get_current_time, search_knowledge
from loguru import logger


async def demo_with_tools():
    print("\n" + "=" * 60)
    print("测试大脑模块 + 真实工具")
    print("=" * 60)

    # 创建大脑实例
    brain = get_brain_manager()

    # 注册真实工具
    brain.register_tools([get_current_time, search_knowledge])

    print(f"✅ 已注册工具: {brain.list_tools()}")

    # 测试 1: 获取当前时间
    print("\n" + "-" * 40)
    print("测试 1: 获取当前时间")
    question = "现在几点了？"
    print(f"用户: {question}")

    response = await brain.think(
        user_input=question,
        session_id="test-tools",
        perception_context={},
        available_tools=[
            {"name": "get_current_time", "description": "获取当前时间"},
            {"name": "search_knowledge", "description": "搜索知识库"}
        ]
    )

    print(f"\n🤖 回答: {response.answer}")

    # 显示工具调用详情
    for step in response.execution_history:
        if step.action.type.value == "tool_call":
            print(f"\n🔧 工具调用详情:")
            print(f"   工具: {step.action.tool_name}")
            print(f"   参数: {step.action.tool_input}")
            print(f"   结果: {step.result}")

    # 测试 2: 知识搜索
    print("\n" + "-" * 40)
    print("测试 2: 知识搜索")
    question2 = "什么是 RAG 技术？"
    print(f"用户: {question2}")

    response2 = await brain.think(
        user_input=question2,
        session_id="test-tools",
        perception_context={},
        available_tools=[
            {"name": "get_current_time", "description": "获取当前时间"},
            {"name": "search_knowledge", "description": "搜索知识库"}
        ]
    )

    print(f"\n🤖 回答: {response2.answer[:300]}...")


async def main():
    await demo_with_tools()


if __name__ == "__main__":
    asyncio.run(main())