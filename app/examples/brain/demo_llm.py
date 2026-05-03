# app/examples/test_brain_simple.py
"""简单的大脑模块测试 - 用于诊断"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


async def demo_llm_connection():
    """测试 LLM 连接"""
    print("\n" + "=" * 60)
    print("测试 LLM 连接")
    print("=" * 60)

    from app.brain.llm_client import get_llm_client
    from langchain_core.messages import HumanMessage, SystemMessage

    try:
        llm = get_llm_client(timeout=10)

        messages = [
            SystemMessage(content="你是一个助手，请简洁回答"),
            HumanMessage(content="说你好")
        ]

        print("正在调用 LLM...")
        response = await llm.invoke(messages)
        print(f"✅ LLM 响应: {response}")
        return True

    except Exception as e:
        print(f"❌ LLM 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def demo_brain_simple():
    """测试大脑模块（最简版本）"""
    print("\n" + "=" * 60)
    print("测试大脑模块（简化版）")
    print("=" * 60)

    from app.brain import BrainManager

    brain = BrainManager()

    question = "你好"
    print(f"\n📝 用户: {question}")

    try:
        response = await brain.think(
            user_input=question,
            session_id="test-simple",
            perception_context={}
        )
        print(f"🤖 回答: {response.answer[:200]}")
        print(f"✅ 测试成功")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🧠 大脑模块诊断测试")

    # 测试1: LLM 连接
    llm_ok = await demo_llm_connection()

    if not llm_ok:
        print("\n⚠️ LLM 连接失败，请检查：")
        print("  1. 网络连接是否正常")
        print("  2. API Key 是否有效")
        print("  3. 是否能够访问 dashscope.aliyuncs.com")
        return

    # 测试2: 大脑模块
    await demo_brain_simple()


if __name__ == "__main__":
    asyncio.run(main())