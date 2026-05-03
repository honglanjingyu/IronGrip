# app/memory/reranker.py
"""重排序模块 - 支持 DashScope Rerank"""

from typing import List, Tuple
import aiohttp
import asyncio
from loguru import logger

from .config import memory_config
from langchain_core.documents import Document


class Reranker:
    """重排序器 - 优化检索结果排序"""

    def __init__(self):
        self.rerank_type = memory_config.RERANK_TYPE
        self.model = memory_config.RERANK_MODEL
        self.api_url = memory_config.RERANK_API_URL
        self.api_key = memory_config.LLM_API_KEY

        logger.info(f"Reranker 初始化: type={self.rerank_type}, model={self.model}")

    async def rerank(
            self,
            query: str,
            documents: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """
        对检索结果进行重排序

        Args:
            query: 查询文本
            documents: 原始检索结果列表 [(doc, score), ...]

        Returns:
            重排序后的结果列表
        """
        if not documents or len(documents) <= 1:
            return documents

        if self.rerank_type == "remote":
            return await self._remote_rerank(query, documents)
        elif self.rerank_type == "local":
            return await self._local_rerank(query, documents)
        else:
            # 不重排序，按原分数排序
            return sorted(documents, key=lambda x: x[1], reverse=True)

    async def _remote_rerank(
            self,
            query: str,
            documents: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """使用 DashScope API 进行重排序"""
        if not self.api_key:
            logger.warning("未配置 API Key，跳过重排序")
            return documents

        try:
            texts = [doc.page_content for doc, _ in documents]

            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": self.model,
                "input": {
                    "query": query,
                    "documents": texts
                },
                "parameters": {
                    "top_n": len(texts)
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        reranked_scores = result.get("output", {}).get("results", [])

                        # 重新排序
                        reranked = []
                        for item in reranked_scores:
                            idx = item.get("index", 0)
                            if idx < len(documents):
                                doc, original_score = documents[idx]
                                reranked.append((doc, item.get("relevance_score", original_score)))

                        logger.info(f"远程重排序完成: {len(reranked)} 条结果")
                        return reranked
                    else:
                        logger.warning(f"重排序 API 请求失败: {response.status}")
                        return documents

        except asyncio.TimeoutError:
            logger.warning("重排序 API 超时，使用原始排序")
            return documents
        except Exception as e:
            logger.warning(f"重排序失败: {e}，使用原始排序")
            return documents

    async def _local_rerank(
            self,
            query: str,
            documents: List[Tuple[Document, float]]
    ) -> List[Tuple[Document, float]]:
        """本地重排序（暂未实现，返回原始排序）"""
        # TODO: 实现本地重排序模型
        logger.debug("本地重排序暂未实现，使用原始排序")
        return documents


# 全局单例
_reranker = None


def get_reranker() -> Reranker:
    """获取全局重排序器实例"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker