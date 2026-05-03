"""记忆检索模块 - 从短期和长期记忆检索信息"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import deque
from loguru import logger

from .models import MemoryItem, MemoryType


class ShortTermMemory:
    """短期记忆 - 最近对话上下文"""

    def __init__(self, max_size: int = 20):
        """
        初始化短期记忆

        Args:
            max_size: 最大消息数量（默认20条，约10轮对话）
        """
        self.messages: deque = deque(maxlen=max_size)
        self.max_size = max_size
        logger.info(f"ShortTermMemory 初始化: max_size={max_size}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })

    def get_recent(self, n: int = 10) -> List[Dict]:
        """获取最近的 N 条消息"""
        return list(self.messages)[-n:]

    def get_all(self) -> List[Dict]:
        """获取所有消息"""
        return list(self.messages)

    def clear(self):
        """清空记忆"""
        self.messages.clear()
        logger.info("短期记忆已清空")


class LongTermMemory:
    """长期记忆 - 向量知识库检索（抽象接口）"""

    def __init__(self, vector_store_manager=None):
        """
        初始化长期记忆

        Args:
            vector_store_manager: 向量存储管理器实例（可选，用于实际检索）
        """
        self.vector_store = vector_store_manager
        logger.info("LongTermMemory 初始化完成")

    async def retrieve(
        self,
        query: str,
        top_k: int = 3
    ) -> List[MemoryItem]:
        """
        从知识库检索相关记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            List[MemoryItem]: 相关记忆条目
        """
        if self.vector_store is None:
            logger.warning("向量存储未配置，返回空结果")
            return []

        try:
            # 执行向量检索
            docs = self.vector_store.similarity_search(query, k=top_k)

            memory_items = []
            for i, doc in enumerate(docs):
                item = MemoryItem(
                    id=str(uuid.uuid4()),
                    type=MemoryType.LONG_TERM,
                    content=doc.page_content,
                    metadata=doc.metadata,
                    score=1.0 - (i * 0.1)  # 模拟分数
                )
                memory_items.append(item)

            logger.info(f"长期记忆检索: query='{query[:50]}...', 返回={len(memory_items)} 条")
            return memory_items

        except Exception as e:
            logger.error(f"长期记忆检索失败: {e}")
            return []

    async def add_knowledge(self, content: str, metadata: Optional[Dict] = None):
        """
        添加知识到长期记忆

        Args:
            content: 知识内容
            metadata: 元数据
        """
        if self.vector_store is None:
            logger.warning("向量存储未配置，无法添加知识")
            return

        try:
            from langchain_core.documents import Document
            doc = Document(page_content=content, metadata=metadata or {})
            self.vector_store.add_documents([doc])
            logger.info(f"添加知识到长期记忆: 长度={len(content)}")
        except Exception as e:
            logger.error(f"添加知识失败: {e}")


class WorkingMemory:
    """工作记忆 - 当前任务的中间结果"""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        logger.info("WorkingMemory 初始化完成")

    def set(self, key: str, value: Any):
        """设置工作记忆"""
        self._data[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        logger.debug(f"工作记忆更新: {key}={str(value)[:50]}...")

    def get(self, key: str, default=None) -> Any:
        """获取工作记忆"""
        if key in self._data:
            return self._data[key]["value"]
        return default

    def get_all(self) -> Dict[str, Any]:
        """获取所有工作记忆"""
        return {k: v["value"] for k, v in self._data.items()}

    def clear(self):
        """清空工作记忆"""
        self._data.clear()
        logger.info("工作记忆已清空")

    def get_summary(self) -> str:
        """获取工作记忆摘要"""
        if not self._data:
            return "无工作记忆"

        summary_parts = []
        for key, value in self._data.items():
            val_str = str(value["value"])
            if len(val_str) > 100:
                val_str = val_str[:100] + "..."
            summary_parts.append(f"- {key}: {val_str}")

        return "\n".join(summary_parts)


class MemoryRetriever:
    """
    记忆检索器 - 统一管理短期、长期和工作记忆
    """

    def __init__(self, vector_store_manager=None):
        """
        初始化记忆检索器

        Args:
            vector_store_manager: 向量存储管理器（用于长期记忆）
        """
        self.short_term = ShortTermMemory(max_size=20)
        self.long_term = LongTermMemory(vector_store_manager)
        self.working = WorkingMemory()
        logger.info("MemoryRetriever 初始化完成")

    async def retrieve_all(
        self,
        query: str,
        session_id: str,
        include_long_term: bool = True,
        top_k: int = 3
    ) -> tuple[List[MemoryItem], List[MemoryItem], Dict[str, Any]]:
        """
        检索所有类型的记忆

        Args:
            query: 查询文本
            session_id: 会话ID
            include_long_term: 是否包含长期记忆
            top_k: 长期记忆返回数量

        Returns:
            tuple: (短期记忆列表, 长期记忆列表, 工作记忆)
        """
        # 短期记忆
        recent_messages = self.short_term.get_recent(n=10)
        short_term_items = []
        for msg in recent_messages:
            item = MemoryItem(
                id=str(uuid.uuid4()),
                type=MemoryType.SHORT_TERM,
                content=f"{msg['role']}: {msg['content']}",
                metadata=msg.get("metadata", {}),
                score=1.0
            )
            short_term_items.append(item)

        # 长期记忆
        long_term_items = []
        if include_long_term:
            long_term_items = await self.long_term.retrieve(query, top_k=top_k)

        # 工作记忆
        working_memory = self.working.get_all()

        logger.info(
            f"记忆检索完成: session={session_id}, "
            f"短期={len(short_term_items)}, 长期={len(long_term_items)}, "
            f"工作记忆键数={len(working_memory)}"
        )

        return short_term_items, long_term_items, working_memory

    def add_to_short_term(self, user_input: str, assistant_output: str):
        """添加对话到短期记忆"""
        self.short_term.add_message("user", user_input)
        self.short_term.add_message("assistant", assistant_output)

    def add_to_working(self, key: str, value: Any):
        """添加到工作记忆"""
        self.working.set(key, value)

    async def add_to_long_term(self, content: str, metadata: Optional[Dict] = None):
        """添加到长期记忆"""
        await self.long_term.add_knowledge(content, metadata)

    def clear_session(self):
        """清空当前会话的所有记忆"""
        self.short_term.clear()
        self.working.clear()
        logger.info("会话记忆已清空")