# nexus/app/a2a/discovery.py
"""
A2A Agent 发现客户端 - 从 .well-known/agent.json 获取 Agent 信息
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from loguru import logger
from pydantic import BaseModel, Field


class AgentSkill(BaseModel):
    """Agent 技能"""
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)


class AgentCapabilities(BaseModel):
    """Agent 能力"""
    streaming: bool = True
    memory: bool = True
    rerank: bool = True
    query_rewrite: bool = True


class AgentCard(BaseModel):
    """从 .well-known/agent.json 获取的 Agent 信息"""
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    url: str
    skills: List[AgentSkill] = Field(default_factory=list)
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    endpoints: Dict[str, str] = Field(default_factory=dict)
    provider: str = ""


@dataclass
class DiscoveredAgent:
    """发现的 Agent 信息"""
    id: str
    name: str
    description: str
    version: str
    base_url: str
    endpoints: Dict[str, str]
    capabilities: AgentCapabilities
    skills: List[AgentSkill]
    is_healthy: bool = False

    def get_endpoint(self, name: str) -> Optional[str]:
        """获取指定名称的端点 URL"""
        if name in self.endpoints:
            return self.endpoints[name]

        # 根据名称推断默认端点
        default_endpoints = {
            "health": f"{self.base_url}/a2a/health",
            "rag_search": f"{self.base_url}/a2a/rag/search",
            "rag_ask": f"{self.base_url}/a2a/rag/ask"
        }
        return default_endpoints.get(name)


class AgentDiscoveryClient:
    """
    A2A Agent 发现客户端

    通过访问目标的 .well-known/agent.json 来发现 Agent 的能力
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._cache: Dict[str, DiscoveredAgent] = {}

    async def discover_agent(self, base_url: str, use_cache: bool = True) -> Optional[DiscoveredAgent]:
        """
        发现指定地址的 Agent

        Args:
            base_url: Agent 服务的基础 URL
            use_cache: 是否使用缓存

        Returns:
            DiscoveredAgent: 发现的 Agent 信息，失败返回 None
        """
        # 规范化 URL
        base_url = base_url.rstrip('/')

        # 检查缓存
        if use_cache and base_url in self._cache:
            cached = self._cache[base_url]
            logger.info(f"使用缓存的 Agent 信息: {base_url}")
            return cached

        # 尝试获取 agent.json
        discovery_urls = [
            f"{base_url}/.well-known/agent.json",
            f"{base_url}/.well-known/agent-card",
            f"{base_url}/a2a/discovery"
        ]

        agent_card = None

        for url in discovery_urls:
            logger.info(f"尝试发现 Agent: {url}")
            card = await self._fetch_agent_card(url)
            if card:
                agent_card = card
                logger.info(f"成功发现 Agent: {url}")
                break

        if not agent_card:
            # 回退：从健康检查推断基本信息
            logger.warning(f"无法发现 Agent，尝试回退模式: {base_url}")
            return await self._fallback_discovery(base_url)

        # 检查健康状态
        health_endpoint = agent_card.endpoints.get("health", f"{base_url}/a2a/health")
        is_healthy = await self._check_health(health_endpoint)

        discovered = DiscoveredAgent(
            id=agent_card.id,
            name=agent_card.name,
            description=agent_card.description,
            version=agent_card.version,
            base_url=base_url,
            endpoints=agent_card.endpoints,
            capabilities=agent_card.capabilities,
            skills=agent_card.skills,
            is_healthy=is_healthy
        )

        # 缓存
        self._cache[base_url] = discovered

        return discovered

    async def _fetch_agent_card(self, url: str) -> Optional[AgentCard]:
        """获取 Agent 卡片"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return AgentCard(**data)
                    else:
                        logger.debug(f"获取 Agent 卡片失败: HTTP {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.debug(f"获取 Agent 卡片超时: {url}")
            return None
        except Exception as e:
            logger.debug(f"获取 Agent 卡片异常: {url}, {e}")
            return None

    async def _check_health(self, health_url: str) -> bool:
        """检查 Agent 健康状态"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("status") == "healthy" or data.get("agent_name") is not None
                    return False
        except Exception:
            return False

    async def _fallback_discovery(self, base_url: str) -> Optional[DiscoveredAgent]:
        """回退发现模式：仅通过健康检查获取基本信息"""
        health_url = f"{base_url}/a2a/health"

        is_healthy = await self._check_health(health_url)

        if not is_healthy:
            logger.warning(f"回退发现失败: Agent 不可用 {base_url}")
            return None

        # 构建基本端点
        endpoints = {
            "health": health_url,
            "rag_search": f"{base_url}/a2a/rag/search",
            "rag_ask": f"{base_url}/a2a/rag/ask"
        }

        return DiscoveredAgent(
            id="unknown",
            name="PaperReadingRAG",
            description="RAG Agent (通过回退发现)",
            version="1.0.0",
            base_url=base_url,
            endpoints=endpoints,
            capabilities=AgentCapabilities(),
            skills=[],
            is_healthy=True
        )

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()

    def get_cached_agent(self, base_url: str) -> Optional[DiscoveredAgent]:
        """获取缓存的 Agent 信息"""
        return self._cache.get(base_url.rstrip('/'))


# 全局发现客户端
_discovery_client: Optional[AgentDiscoveryClient] = None


def get_discovery_client() -> AgentDiscoveryClient:
    """获取全局发现客户端"""
    global _discovery_client
    if _discovery_client is None:
        _discovery_client = AgentDiscoveryClient()
    return _discovery_client