# demo_a2a.py
"""测试 A2A 通信"""

import asyncio
import aiohttp


async def demo_a2a():
    """测试 A2A 通信"""

    # 测试 PaperReadingRAG A2A 服务
    print("=" * 60)
    print("测试 A2A 服务")
    print("=" * 60)

    # 1. 健康检查
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8001/a2a/health") as resp:
            health = await resp.json()
            print(f"健康检查: {health}")

    # 2. 测试 RAG 检索
    async with aiohttp.ClientSession() as session:
        request = {
            "query": "世运电子的主营业务是什么？",
            "top_k": 3,
            "need_answer": True
        }
        async with session.post(
                "http://localhost:8001/a2a/rag/search",
                json=request
        ) as resp:
            result = await resp.json()
            print(f"\nRAG 检索结果:")
            print(f"  成功: {result.get('success')}")
            print(f"  答案: {result.get('answer', '无')[:200]}...")
            if result.get('documents'):
                print(f"  文档数: {len(result.get('documents'))}")

    # 3. 测试 Nexus 通过 A2A 调用
    print("\n" + "=" * 60)
    print("测试 Nexus 调用")
    print("=" * 60)

    async with aiohttp.ClientSession() as session:
        # 模拟 Nexus 的聊天请求
        chat_request = {
            "message": "帮我查一下世运电子的主要业务是什么？",
            "session_id": "test_session_001"
        }
        async with session.post(
                "http://localhost:8002/api/v1/chat",
                json=chat_request
        ) as resp:
            result = await resp.json()
            print(f"Nexus 响应:")
            print(f"  成功: {result.get('success')}")
            print(f"  回答: {result.get('response', '无')[:300]}...")


if __name__ == "__main__":
    asyncio.run(demo_a2a())