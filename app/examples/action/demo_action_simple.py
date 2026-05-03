# examples/action/demo_action_simple_fixed.py
# !/usr/bin/env python
"""行动模块简单演示 - 修复版"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.action import get_action_manager, ActionType


async def simple_demo():
    print("=" * 50)
    print("行动模块简单示例")
    print("=" * 50)

    manager = get_action_manager()
    manager.register_builtin_tools()

    print(f"已注册工具: {manager.list_tools()}")

    # 测试时间查询（不需要外部服务）
    print("\n1. 查询当前时间...")
    result = await manager.run_single_action(
        action_type=ActionType.TOOL_CALL,
        tool_name="get_current_time",
        tool_input={}
    )
    print(f"   结果: {result.result}")

    print("\n2. 查询知识库统计...")
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