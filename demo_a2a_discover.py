# test_a2a_discovery.py
"""
测试 A2A Agent 发现机制
"""

import asyncio
import aiohttp
import json


async def demo_paperreadingrag_discovery():
    """测试 PaperReadingRAG 的发现端点"""
    print("=" * 60)
    print("测试 PaperReadingRAG Agent 发现")
    print("=" * 60)

    base_url = "http://localhost:8001"

    # 测试标准发现端点
    discovery_urls = [
        f"{base_url}/.well-known/agent.json",
        f"{base_url}/.well-known/agent-card",
        f"{base_url}/a2a/capabilities",
        f"{base_url}/a2a/info"
    ]

    async with aiohttp.ClientSession() as session:
        for url in discovery_urls:
            print(f"\n📡 尝试: {url}")
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"   ✅ 成功")
                        print(f"   Agent: {data.get('name', 'N/A')}")
                        print(f"   Version: {data.get('version', 'N/A')}")
                        if 'skills' in data:
                            print(
                                f"   Skills: {[s.get('name', s) if isinstance(s, dict) else s for s in data['skills'][:3]]}")
                    else:
                        print(f"   ❌ HTTP {resp.status}")
            except Exception as e:
                print(f"   ❌ 错误: {e}")


async def demo_nexus_discovery():
    """测试 Nexus 的发现客户端"""
    print("\n" + "=" * 60)
    print("测试 Nexus Agent 发现客户端")
    print("=" * 60)

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent / "nexus"))

    from app.a2a.discovery import AgentDiscoveryClient
    from app.a2a.client import A2AClient

    # 测试发现客户端
    discovery = AgentDiscoveryClient()

    rag_agent = await discovery.discover_agent("http://localhost:8001")

    if rag_agent:
        print(f"\n✅ 发现 Agent:")
        print(f"   ID: {rag_agent.id}")
        print(f"   Name: {rag_agent.name}")
        print(f"   Version: {rag_agent.version}")
        print(f"   Health: {'✅' if rag_agent.is_healthy else '❌'}")
        print(f"   Skills:")
        for skill in rag_agent.skills:
            print(f"     - {skill.name}: {skill.description[:50]}...")
        print(f"   Endpoints:")
        for name, url in rag_agent.endpoints.items():
            print(f"     - {name}: {url}")
    else:
        print("\n❌ 发现失败")

    # 测试 A2A 客户端
    print("\n" + "=" * 60)
    print("测试 A2A 客户端自动发现")
    print("=" * 60)

    client = A2AClient(base_url="http://localhost:8001", auto_discover=True)

    # 获取 Agent 信息
    info = await client.get_agent_info()
    if info:
        print(f"\n📋 Agent 信息:")
        print(f"   Name: {info['name']}")
        print(f"   Capabilities: {info['capabilities']}")

    # 测试问答
    print("\n📝 测试问答:")
    result = await client.rag_ask("什么是 RAG 技术？", top_k=3)
    if result.get("success"):
        answer = result.get("answer", "")
        print(f"   Answer: {answer[:200]}...")
    else:
        print(f"   Error: {result.get('error')}")

    await client.close()


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("A2A Agent 发现机制测试")
    print("=" * 60)
    print("\n请确保 PaperReadingRAG 服务已启动:")
    print("  cd paperreadingrag")
    print("  python run_api.py --port 8001")
    print("\n开始测试...\n")

    await demo_paperreadingrag_discovery()
    await demo_nexus_discovery()


if __name__ == "__main__":
    asyncio.run(main())