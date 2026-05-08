# nexus/app/a2a/client.py
"""
A2A 客户端 - 调用 PaperReadingRAG 的 RAG 能力
"""

import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from pydantic import BaseModel, Field


class A2ARAGRequest(BaseModel):
    """A2A RAG 请求"""
    query: str
    session_id: Optional[str] = None
    top_k: int = 5
    recall_k: int = 10
    need_answer: bool = True
    include_documents: bool = True


class A2ARAGResponse(BaseModel):
    """A2A RAG 响应"""
    success: bool
    answer: Optional[str] = None
    documents: Optional[List[Dict]] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


class A2AClient:
    """
    A2A 客户端 - 调用 PaperReadingRAG 的 RAG 能力

    通过标准 HTTP 协议与其他 Agent 通信
    """

    def __init__(
            self,
            base_url: str = "http://localhost:8001",
            timeout: int = 60
    ):
        """
        初始化 A2A 客户端

        Args:
            base_url: PaperReadingRAG 的 A2A 服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"A2A 客户端初始化: {base_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def health_check(self) -> Dict[str, Any]:
        """检查 A2A 服务健康状态"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/a2a/health") as resp:
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
        """
        调用 PaperReadingRAG 进行 RAG 检索

        Args:
            query: 查询问题
            session_id: 会话ID（用于保持上下文）
            top_k: 返回文档数量
            recall_k: 召回数量
            need_answer: 是否生成答案
            include_documents: 是否包含检索文档

        Returns:
            A2ARAGResponse: 检索结果
        """
        logger.info(f"A2A: 调用 RAG 检索: query='{query[:50]}...'")

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
            async with session.post(
                    f"{self.base_url}/a2a/rag/search",
                    json=request.dict()
            ) as resp:
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
        """
        简化的 A2A 问答接口

        Args:
            query: 查询问题
            session_id: 会话ID
            top_k: 返回文档数量

        Returns:
            Dict: 包含 answer, success, error 的字典
        """
        result = await self.rag_search(
            query=query,
            session_id=session_id,
            top_k=top_k,
            need_answer=True
        )

        return {
            "success": result.success,
            "answer": result.answer,
            "session_id": result.session_id,
            "error": result.error
        }

    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("A2A 客户端已关闭")


# 全局单例
_a2a_client: Optional[A2AClient] = None


def get_a2a_client(base_url: str = "http://localhost:8001") -> A2AClient:
    """获取 A2A 客户端单例"""
    global _a2a_client
    if _a2a_client is None:
        _a2a_client = A2AClient(base_url=base_url)
    return _a2a_client