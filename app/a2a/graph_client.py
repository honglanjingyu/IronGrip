# app/a2a/graph_client.py
"""
GraphRAG 客户端 - 调用 PaperReadingRAG 的知识图谱增强检索
"""

import os
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any, AsyncGenerator
from loguru import logger


class GraphRAGClient:
    """
    GraphRAG 客户端 - 调用 PaperReadingRAG 的 GraphRAG 接口
    """

    def __init__(
            self,
            base_url: str = None,
            timeout: int = 120  # 增加到 120 秒
    ):
        self.base_url = (base_url or os.getenv("PAPERREADINGRAG_URL", "http://localhost:8001")).rstrip('/')
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"GraphRAG 客户端初始化: {self.base_url}, timeout={timeout}s")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # 增加连接超时和读取超时
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10,
                sock_read=self.timeout
            )
            connector = aiohttp.TCPConnector(limit=10, force_close=True)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self._session

    async def graph_ask(
            self,
            question: str,
            session_id: Optional[str] = None,
            top_k: int = 8,
            enable_memory: bool = True
    ) -> Dict[str, Any]:
        """调用 GraphRAG 问答接口（非流式）"""
        logger.info(f"GraphRAG 调用: {question[:50]}...")

        url = f"{self.base_url}/api/chat/graph/ask"
        payload = {
            "question": question,
            "session_id": session_id,
            "top_k": top_k,
            "enable_memory": enable_memory
        }

        try:
            session = await self._get_session()

            logger.info(f"发送请求到: {url}")
            logger.debug(f"请求参数: {payload}")

            async with session.post(url, json=payload) as resp:
                logger.info(f"响应状态码: {resp.status}")

                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"GraphRAG 响应成功, answer长度={len(data.get('answer', ''))}")
                    return data
                else:
                    error_text = await resp.text()
                    logger.error(f"GraphRAG 请求失败: HTTP {resp.status} - {error_text[:500]}")
                    return {
                        "success": False,
                        "error": f"HTTP {resp.status}: {error_text[:200]}"
                    }

        except asyncio.TimeoutError:
            logger.error(f"GraphRAG 请求超时 (超过 {self.timeout} 秒)")
            return {"success": False, "error": f"请求超时，请稍后重试"}

        except aiohttp.ClientConnectorError as e:
            logger.error(f"GraphRAG 连接失败: {e}")
            return {"success": False, "error": f"无法连接到 {self.base_url}，请确保 PaperReadingRAG 服务已启动"}

        except aiohttp.ClientResponseError as e:
            logger.error(f"GraphRAG 响应错误: {e}")
            return {"success": False, "error": f"服务响应错误: {e.status}"}

        except Exception as e:
            logger.error(f"GraphRAG 请求异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    async def graph_ask_stream(
            self,
            question: str,
            session_id: Optional[str] = None,
            top_k: int = 8,
            enable_memory: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用 GraphRAG 问答接口

        Yields:
            事件字典，包含 type 和 data
        """
        logger.info(f"GraphRAG 流式调用: {question[:50]}...")

        url = f"{self.base_url}/api/chat/graph/ask/stream"
        payload = {
            "question": question,
            "session_id": session_id,
            "top_k": top_k,
            "enable_memory": enable_memory
        }

        try:
            session = await self._get_session()

            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"GraphRAG 流式请求失败: HTTP {resp.status} - {error_text[:200]}")
                    yield {"type": "error", "data": f"HTTP {resp.status}: {error_text[:200]}"}
                    return

                # 解析 NDJSON 流
                async for line in resp.content:
                    if line:
                        try:
                            event = json.loads(line.decode('utf-8').strip())
                            yield event
                        except Exception as e:
                            logger.warning(f"解析流式响应失败: {e}")
                            continue

        except asyncio.TimeoutError:
            logger.error(f"GraphRAG 流式请求超时")
            yield {"type": "error", "data": "请求超时，请稍后重试"}

        except Exception as e:
            logger.error(f"GraphRAG 流式请求失败: {e}")
            yield {"type": "error", "data": str(e)}

    async def health_check(self) -> bool:
        """检查服务健康状态"""
        try:
            session = await self._get_session()
            # 尝试多个健康检查端点
            endpoints = [
                f"{self.base_url}/api/health",
                f"{self.base_url}/health",
                f"{self.base_url}/a2a/health",
            ]

            for url in endpoints:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            logger.debug(f"健康检查成功: {url}")
                            return True
                except Exception:
                    continue

            logger.warning(f"所有健康检查端点都失败")
            return False

        except Exception as e:
            logger.warning(f"健康检查失败: {e}")
            return False

    async def close(self):
        """关闭客户端"""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("GraphRAG 客户端已关闭")


# 全局单例
_graph_client: Optional[GraphRAGClient] = None


def get_graph_client() -> GraphRAGClient:
    """获取 GraphRAG 客户端单例"""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphRAGClient()
    return _graph_client