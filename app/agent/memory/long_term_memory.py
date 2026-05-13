# app/memory/long_term_memory.py
"""长期记忆 - 向量知识库存储（只支持 Milvus）"""

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
    长期记忆 - 只支持 Milvus 向量存储
    """

    def __init__(
            self,
            vector_store=None,
            config: Optional[LongTermConfig] = None
    ):
        self.config = config or LongTermConfig(
            top_k=memory_config.SIMILARITY_TOP_K,
            similarity_threshold=memory_config.SIMILARITY_THRESHOLD,
            enable_hybrid_search=False,
            vector_weight=memory_config.HYBRID_VECTOR_WEIGHT,
            keyword_weight=memory_config.HYBRID_KEYWORD_WEIGHT
        )

        # 创建向量存储（只支持 Milvus）
        if vector_store is not None:
            self.vector_store = vector_store
        elif memory_config.ENABLE_STORAGE:
            self.vector_store = MilvusVectorStore()
        else:
            self.vector_store = None
            logger.warning("向量存储已禁用")

        # 重排序器
        self.reranker = get_reranker()

        logger.info(f"LongTermMemory 初始化完成: top_k={self.config.top_k}, threshold={self.config.similarity_threshold}")

    async def retrieve(
            self,
            query: str,
            session_id: Optional[str] = None,
            top_k: Optional[int] = None,
            score_threshold: Optional[float] = None,
            filter_metadata: Optional[Dict[str, Any]] = None,
            enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """从长期记忆检索相关条目"""
        if self.vector_store is None:
            logger.warning("向量存储未配置，返回空结果")
            return []

        top_k = top_k or self.config.top_k
        score_threshold = score_threshold or self.config.similarity_threshold

        # 构建过滤条件
        combined_filter = {}
        if filter_metadata:
            combined_filter.update(filter_metadata)
        if session_id:
            combined_filter["session_id"] = session_id

        try:
            retrieve_k = top_k * 2 if enable_rerank else top_k

            results = self.vector_store.similarity_search_with_score(
                query, retrieve_k, combined_filter if combined_filter else None
            )

            results = [(doc, score) for doc, score in results if score >= score_threshold]

            if enable_rerank and self.reranker.rerank_type != "none":
                results = await self.reranker.rerank(query, results)
                results = results[:top_k]
            else:
                results = sorted(results, key=lambda x: x[1], reverse=True)[:top_k]

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

    async def add_knowledge(
            self,
            content: str,
            session_id: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            doc_id: Optional[str] = None
    ) -> bool:
        """添加知识到长期记忆"""
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

    def get_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息"""
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