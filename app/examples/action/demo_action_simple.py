#!/usr/bin/env python
"""行动模块简单示例"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.action import get_action_manager, ActionType, OutputType


async def simple_demo():
    """简单演示"""
    print("🧠 行动模块简单示例")
    print("=" * 40)

    # 获取行动管理器
    manager = get_action_manager()

    # 注册内置工具
    manager.register_builtin_tools()
    print(f"✅ 已注册工具: {manager.list_tools()}")

    # 执行时间查询
    print("\n1️⃣ 查询当前时间...")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_current_time",
        tool_input={}
    )
    print(f"   结果: {result.result}")

    # 查询知识库
    print("\n2️⃣ 查询知识库...")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_knowledge_stats",
        tool_input={}
    )
    print(f"   结果: {result.result}")

    print("\n✅ 演示完成!")


async def main():
    await simple_demo()


if __name__ == "__main__":
    asyncio.run(main())