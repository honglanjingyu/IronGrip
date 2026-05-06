# app/memory/long_term_memory.py
"""长期记忆 - 向量知识库存储（支持会话隔离）"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
from langchain_core.documents import Document

from .models import MemoryItem, MemoryType, LongTermConfig
from .config import memory_config
from .milvus_store import MilvusVectorStore
from .reranker import get_reranker
from datetime import datetime


class LongTermMemory:
    """
    长期记忆 - 支持会话隔离

    特点：
    - 使用 Milvus 向量数据库存储
    - 支持按会话过滤
    - 支持语义搜索
    - 支持重排序优化
    - 支持元数据过滤
    """

    def __init__(
            self,
            vector_store=None,
            config: Optional[LongTermConfig] = None
    ):
        """
        初始化长期记忆

        Args:
            vector_store: 向量存储实例，默认自动创建 MilvusVectorStore
            config: 配置，默认使用 LongTermConfig()
        """
        self.config = config or LongTermConfig(
            top_k=memory_config.SIMILARITY_TOP_K,
            similarity_threshold=memory_config.SIMILARITY_THRESHOLD,
            enable_hybrid_search=False,
            vector_weight=memory_config.HYBRID_VECTOR_WEIGHT,
            keyword_weight=memory_config.HYBRID_KEYWORD_WEIGHT
        )

        # 创建向量存储
        if vector_store is not None:
            self.vector_store = vector_store
        elif memory_config.ENABLE_STORAGE and memory_config.VECTOR_STORE_TYPE == "milvus":
            self.vector_store = MilvusVectorStore()
        else:
            self.vector_store = None
            logger.warning("向量存储未配置或配置错误")

        # 重排序器
        self.reranker = get_reranker()

        logger.info(
            f"LongTermMemory 初始化完成: top_k={self.config.top_k}, threshold={self.config.similarity_threshold}")

    async def retrieve(
            self,
            query: str,
            session_id: Optional[str] = None,
            top_k: Optional[int] = None,
            score_threshold: Optional[float] = None,
            filter_metadata: Optional[Dict[str, Any]] = None,
            enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """
        从长期记忆检索相关条目（支持会话隔离）

        Args:
            query: 查询文本
            session_id: 会话ID（用于过滤）
            top_k: 返回数量，默认使用配置值
            score_threshold: 相似度阈值，默认使用配置值
            filter_metadata: 额外的元数据过滤条件
            enable_rerank: 是否启用重排序

        Returns:
            List[MemoryItem]: 相关记忆条目列表
        """
        if self.vector_store is None:
            logger.warning("向量存储未配置，返回空结果")
            return []

        top_k = top_k or self.config.top_k
        score_threshold = score_threshold or self.config.similarity_threshold

        # 构建过滤条件（包含会话隔离）
        combined_filter = {}
        if filter_metadata:
            combined_filter.update(filter_metadata)
        if session_id:
            combined_filter["session_id"] = session_id

        try:
            # 检索时多取一些，为重排序预留空间
            retrieve_k = top_k * 2 if enable_rerank else top_k

            # 执行搜索
            results = self.vector_store.similarity_search_with_score(
                query, retrieve_k, combined_filter if combined_filter else None
            )

            # 应用分数阈值（初步过滤）
            results = [(doc, score) for doc, score in results if score >= score_threshold]

            # 重排序
            if enable_rerank and self.reranker.rerank_type != "none":
                results = await self.reranker.rerank(query, results)
                results = results[:top_k]
            else:
                # 按分数排序
                results = sorted(results, key=lambda x: x[1], reverse=True)[:top_k]

            # 转换为 MemoryItem
            memory_items = []
            for doc, score in results:
                item = MemoryItem(
                    id=doc.metadata.get("id", ""),
                    type=MemoryType.LONG_TERM,
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=score
                )
                memory_items.append(item)

            logger.info(f"长期记忆检索: session={session_id}, query='{query[:50]}...', 返回={len(memory_items)} 条")
            return memory_items

        except Exception as e:
            logger.error(f"长期记忆检索失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def retrieve_by_session(
            self,
            session_id: str,
            top_k: Optional[int] = None,
            enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """
        检索指定会话的所有记忆（不基于查询）

        Args:
            session_id: 会话ID
            top_k: 返回数量
            enable_rerank: 是否启用重排序

        Returns:
            List[MemoryItem]: 会话的所有记忆条目
        """
        if self.vector_store is None:
            return []

        top_k = top_k or self.config.top_k

        try:
            # 使用空查询或通用查询
            results = self.vector_store.similarity_search_with_score(
                "", top_k, {"session_id": session_id}
            )
            return [
                MemoryItem(
                    id=doc.metadata.get("id", ""),
                    type=MemoryType.LONG_TERM,
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=score
                )
                for doc, score in results
            ]
        except Exception as e:
            logger.error(f"按会话检索失败: {e}")
            return []

    async def retrieve_hybrid(
            self,
            query: str,
            session_id: Optional[str] = None,
            top_k: Optional[int] = None,
            score_threshold: Optional[float] = None,
            filter_metadata: Optional[Dict[str, Any]] = None,
            enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """
        混合检索（向量 + 关键词）- 当前回退到纯向量检索
        """
        # 目前 Milvus 存储不支持混合检索，回退到纯向量检索
        if self.config.enable_hybrid_search and hasattr(self.vector_store, 'hybrid_search'):
            # 如果向量存储支持混合检索
            try:
                # 构建过滤条件
                combined_filter = {}
                if filter_metadata:
                    combined_filter.update(filter_metadata)
                if session_id:
                    combined_filter["session_id"] = session_id

                results = await self.vector_store.hybrid_search(query, top_k, combined_filter)
                # 转换结果...
            except Exception as e:
                logger.warning(f"混合检索失败，回退到向量检索: {e}")

        # 回退到纯向量检索
        return await self.retrieve(query, session_id, top_k, score_threshold, filter_metadata, enable_rerank)

    async def add_knowledge(
            self,
            content: str,
            session_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            doc_id: Optional[str] = None
    ) -> bool:
        """
        添加知识到长期记忆（支持会话隔离）

        Args:
            content: 知识内容
            session_id: 会话ID（用于隔离）
            metadata: 元数据
            doc_id: 文档ID

        Returns:
            bool: 是否成功
        """
        if self.vector_store is None:
            logger.warning("向量存储未配置，无法添加知识")
            return False

        try:
            import uuid

            final_metadata = metadata or {}
            if session_id:
                final_metadata["session_id"] = session_id
            if doc_id:
                final_metadata["id"] = doc_id
            else:
                final_metadata["id"] = str(uuid.uuid4())
            final_metadata["timestamp"] = datetime.now().isoformat()

            doc = Document(page_content=content, metadata=final_metadata)
            ids = self.vector_store.add_documents([doc])

            success = len(ids) > 0
            if success:
                logger.info(f"添加知识到长期记忆: session={session_id}, id={final_metadata['id']}, 长度={len(content)}")
            else:
                logger.warning("添加知识失败")

            return success

        except Exception as e:
            logger.error(f"添加知识失败: {e}")
            return False

    async def delete_by_session(self, session_id: str) -> int:
        """删除指定会话的所有知识"""
        if self.vector_store is None:
            return 0

        try:
            count = self.vector_store.delete_by_session(session_id)
            logger.info(f"删除会话知识: session={session_id}, 数量={count}")
            return count
        except Exception as e:
            logger.error(f"删除会话知识失败: {e}")
            return 0

    async def delete_by_source(self, source: str) -> int:
        """删除指定来源的所有知识"""
        if self.vector_store is None:
            return 0

        try:
            count = self.vector_store.delete_by_source(source)
            logger.info(f"删除知识: source={source}, 数量={count}")
            return count
        except Exception as e:
            logger.error(f"删除知识失败: {e}")
            return 0

    def get_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息（可选按会话）"""
        if self.vector_store is None:
            return {"available": False, "error": "向量存储未配置"}

        stats = self.vector_store.get_collection_stats()
        return {
            "available": True,
            "type": "milvus",
            "collection_name": getattr(self.vector_store, 'collection_name', 'unknown'),
            "num_entities": stats.get('num_entities', 0),
            "session_id": session_id,
            "config": {
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold
            }
        }

    def is_available(self) -> bool:
        """检查长期记忆是否可用"""
        if self.vector_store is None:
            return False

        stats = self.vector_store.get_collection_stats()
        return stats.get('exists', False) and stats.get('num_entities', 0) > 0
