# nexus/app/a2a/client.py (修改版)
"""
A2A 客户端 - 支持通过 .well-known 发现 Agent
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from pydantic import BaseModel, Field

from .discovery import AgentDiscoveryClient, get_discovery_client, DiscoveredAgent


class A2ARAGRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    top_k: int = 5
    recall_k: int = 10
    need_answer: bool = True
    include_documents: bool = True


class A2ARAGResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    documents: Optional[List[Dict]] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


class A2AClient:
    """
    A2A 客户端 - 支持 Agent 发现

    通过访问目标的 .well-known/agent.json 自动发现 Agent 能力
    """

    def __init__(
            self,
            base_url: str = "http://localhost:8001",
            auto_discover: bool = True,
            timeout: int = 60
    ):
        """
        初始化 A2A 客户端

        Args:
            base_url: PaperReadingRAG 的 A2A 服务地址
            auto_discover: 是否自动发现 Agent 能力
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.auto_discover = auto_discover
        self._session: Optional[aiohttp.ClientSession] = None
        self._agent_info: Optional[DiscoveredAgent] = None
        self._discovery_client = get_discovery_client()

        logger.info(f"A2A 客户端初始化: {base_url}")

    async def discover(self, force: bool = False) -> Optional[DiscoveredAgent]:
        """
        发现 Agent 能力

        Args:
            force: 是否强制重新发现

        Returns:
            DiscoveredAgent: Agent 信息
        """
        if not force and self._agent_info:
            return self._agent_info

        self._agent_info = await self._discovery_client.discover_agent(self.base_url)

        if self._agent_info:
            logger.info(f"Agent 发现成功: {self._agent_info.name} v{self._agent_info.version}")
            logger.info(f"  技能: {[s.name for s in self._agent_info.skills]}")
            logger.info(f"  流式支持: {self._agent_info.capabilities.streaming}")
            logger.info(f"  记忆支持: {self._agent_info.capabilities.memory}")
        else:
            logger.warning(f"Agent 发现失败: {self.base_url}")

        return self._agent_info

    async def get_agent_info(self) -> Optional[Dict[str, Any]]:
        """获取 Agent 信息摘要"""
        info = await self.discover()
        if info:
            return {
                "id": info.id,
                "name": info.name,
                "description": info.description,
                "version": info.version,
                "capabilities": {
                    "streaming": info.capabilities.streaming,
                    "memory": info.capabilities.memory
                },
                "skills": [{"name": s.name, "description": s.description} for s in info.skills],
                "is_healthy": info.is_healthy
            }
        return None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def health_check(self) -> Dict[str, Any]:
        """检查 A2A 服务健康状态"""
        # 优先使用发现的端点
        if self._agent_info and "health" in self._agent_info.endpoints:
            health_url = self._agent_info.endpoints["health"]
        else:
            health_url = f"{self.base_url}/a2a/health"

        try:
            session = await self._get_session()
            async with session.get(health_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"A2A 服务健康: {data}")
                    return data
                return {"status": "unhealthy", "error": f"HTTP {resp.status}"}
        except Exception as e:
            logger.error(f"A2A 健康检查失败: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def rag_search(
            self,
            query: str,
            session_id: Optional[str] = None,
            top_k: int = 5,
            recall_k: int = 10,
            need_answer: bool = True,
            include_documents: bool = True
    ) -> A2ARAGResponse:
        """调用 RAG 检索"""
        logger.info(f"A2A: 调用 RAG 检索: query='{query[:50]}...'")

        # 自动发现（如果还没发现）
        if self.auto_discover and not self._agent_info:
            await self.discover()

        # 使用发现的端点或默认端点
        if self._agent_info and "rag_search" in self._agent_info.endpoints:
            search_url = self._agent_info.endpoints["rag_search"]
        else:
            search_url = f"{self.base_url}/a2a/rag/search"

        request = A2ARAGRequest(
            query=query,
            session_id=session_id,
            top_k=top_k,
            recall_k=recall_k,
            need_answer=need_answer,
            include_documents=include_documents
        )

        try:
            session = await self._get_session()
            async with session.post(search_url, json=request.model_dump()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return A2ARAGResponse(**data)
                else:
                    error_text = await resp.text()
                    return A2ARAGResponse(
                        success=False,
                        error=f"HTTP {resp.status}: {error_text[:200]}"
                    )
        except asyncio.TimeoutError:
            logger.error("A2A 请求超时")
            return A2ARAGResponse(
                success=False,
                error="请求超时，请稍后重试"
            )
        except Exception as e:
            logger.error(f"A2A 请求失败: {e}")
            return A2ARAGResponse(
                success=False,
                error=str(e)
            )

    async def rag_ask(
            self,
            query: str,
            session_id: Optional[str] = None,
            top_k: int = 5
    ) -> Dict[str, Any]:
        """简化的 A2A 问答接口"""
        # 自动发现（如果还没发现）
        if self.auto_discover and not self._agent_info:
            await self.discover()

        # 使用发现的端点或默认端点
        if self._agent_info and "rag_ask" in self._agent_info.endpoints:
            ask_url = self._agent_info.endpoints["rag_ask"]
        else:
            ask_url = f"{self.base_url}/a2a/rag/ask"

        request = A2ARAGRequest(
            query=query,
            session_id=session_id,
            top_k=top_k,
            need_answer=True
        )

        try:
            session = await self._get_session()
            async with session.post(ask_url, json=request.model_dump()) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {
                    "success": False,
                    "error": f"HTTP {resp.status}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("A2A 客户端已关闭")


# 全局单例
_a2a_client: Optional[A2AClient] = None


def get_a2a_client(base_url: str = "http://localhost:8001", auto_discover: bool = True) -> A2AClient:
    """获取 A2A 客户端单例"""
    global _a2a_client
    if _a2a_client is None:
        _a2a_client = A2AClient(base_url=base_url, auto_discover=auto_discover)
    return _a2a_client