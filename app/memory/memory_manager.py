# app/memory/memory_manager.py
"""记忆管理器 - 统一管理三种记忆（支持多会话）"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import asyncio

from .models import (
    MemoryItem, MemoryType, MemoryStats,
    ShortTermConfig, LongTermConfig, WorkingMemoryConfig
)
from .short_term_memory import ShortTermMemory
from .working_memory import WorkingMemory
from .long_term_memory import LongTermMemory


class MemoryManager:
    """
    记忆管理器 - 支持多会话

    统一管理：
    - 短期记忆（对话上下文）- 按会话隔离
    - 长期记忆（向量知识库）- 支持按会话过滤
    - 工作记忆（任务中间结果）- 按会话隔离
    """

    def __init__(
            self,
            short_term_config: Optional[ShortTermConfig] = None,
            working_config: Optional[WorkingMemoryConfig] = None,
            long_term_config: Optional[LongTermConfig] = None,
            vector_store=None
    ):
        """
        初始化记忆管理器

        Args:
            short_term_config: 短期记忆配置
            working_config: 工作记忆配置
            long_term_config: 长期记忆配置
            vector_store: 向量存储实例（用于长期记忆）
        """
        # 按会话存储的记忆
        self._short_term_memories: Dict[str, ShortTermMemory] = {}
        self._working_memories: Dict[str, WorkingMemory] = {}
        self._short_term_config = short_term_config or ShortTermConfig()
        self._working_config = working_config or WorkingMemoryConfig()

        # 长期记忆（共享，但支持会话过滤）
        self.long_term = LongTermMemory(vector_store, long_term_config)

        self._current_session_id: Optional[str] = None

        logger.info("MemoryManager 初始化完成（支持多会话）")

    def set_session(self, session_id: str):
        """设置当前会话ID"""
        self._current_session_id = session_id

        # 自动创建会话的记忆实例（如果不存在）
        if session_id not in self._short_term_memories:
            self._short_term_memories[session_id] = ShortTermMemory(self._short_term_config)
            self._working_memories[session_id] = WorkingMemory(self._working_config)
            logger.debug(f"创建新会话记忆: {session_id}")

        logger.debug(f"切换到会话: {session_id}")

    @property
    def short_term(self) -> ShortTermMemory:
        """获取当前会话的短期记忆"""
        if not self._current_session_id:
            raise ValueError("未设置会话，请调用 set_session()")
        return self._short_term_memories[self._current_session_id]

    @property
    def working(self) -> WorkingMemory:
        """获取当前会话的工作记忆"""
        if not self._current_session_id:
            raise ValueError("未设置会话，请调用 set_session()")
        return self._working_memories[self._current_session_id]

    # ========== 短期记忆方法 ==========

    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加用户消息到短期记忆"""
        return self.short_term.add_user_message(content, metadata)

    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加助手消息到短期记忆"""
        return self.short_term.add_assistant_message(content, metadata)

    def add_system_message(self, content: str, metadata: Optional[Dict] = None) -> MemoryItem:
        """添加系统消息到短期记忆"""
        return self.short_term.add_system_message(content, metadata)

    def add_conversation(self, user_input: str, assistant_output: str) -> Tuple[MemoryItem, MemoryItem]:
        """添加完整对话"""
        user_item = self.short_term.add_user_message(user_input)
        assistant_item = self.short_term.add_assistant_message(assistant_output)
        return user_item, assistant_item

    def get_short_term_context(self, max_messages: Optional[int] = None) -> str:
        """获取格式化的短期记忆上下文"""
        return self.short_term.get_formatted_context(max_messages)

    def get_recent_messages(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近的N条消息"""
        return self.short_term.get_recent(n)

    # ========== 工作记忆方法 ==========

    def set_working(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> MemoryItem:
        """设置工作记忆"""
        return self.working.set(key, value, ttl_seconds)

    def get_working(self, key: str, default: Any = None) -> Any:
        """获取工作记忆"""
        return self.working.get(key, default)

    def delete_working(self, key: str) -> bool:
        """删除工作记忆"""
        return self.working.delete(key)

    def get_all_working(self) -> Dict[str, Any]:
        """获取所有工作记忆"""
        return self.working.get_all()

    def get_working_summary(self) -> str:
        """获取工作记忆摘要"""
        return self.working.get_summary()

    # ========== 长期记忆方法 ==========

    async def retrieve_long_term(
            self,
            query: str,
            top_k: Optional[int] = None,
            score_threshold: Optional[float] = None,
            filter_metadata: Optional[Dict[str, Any]] = None,
            use_hybrid: bool = True,
            enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """
        检索长期记忆（自动按当前会话过滤）

        Args:
            query: 查询文本
            top_k: 返回数量
            score_threshold: 相似度阈值
            filter_metadata: 额外的元数据过滤
            use_hybrid: 是否使用混合检索
            enable_rerank: 是否启用重排序

        Returns:
            List[MemoryItem]: 相关记忆条目
        """
        if use_hybrid and self.long_term.config.enable_hybrid_search:
            return await self.long_term.retrieve_hybrid(
                query,
                session_id=self._current_session_id,
                top_k=top_k,
                score_threshold=score_threshold,
                filter_metadata=filter_metadata,
                enable_rerank=enable_rerank
            )
        else:
            return await self.long_term.retrieve(
                query,
                session_id=self._current_session_id,
                top_k=top_k,
                score_threshold=score_threshold,
                filter_metadata=filter_metadata,
                enable_rerank=enable_rerank
            )

    async def add_to_long_term(
            self,
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
            doc_id: Optional[str] = None
    ) -> bool:
        """
        添加知识到长期记忆（自动关联当前会话）

        Args:
            content: 知识内容
            metadata: 元数据
            doc_id: 文档ID

        Returns:
            bool: 是否成功
        """
        return await self.long_term.add_knowledge(
            content,
            session_id=self._current_session_id,
            metadata=metadata,
            doc_id=doc_id
        )

    async def delete_current_session_long_term(self) -> int:
        """删除当前会话的所有长期记忆"""
        if not self._current_session_id:
            return 0
        return await self.long_term.delete_by_session(self._current_session_id)

    async def delete_from_long_term(self, source: str) -> int:
        """从长期记忆删除指定来源的知识"""
        return await self.long_term.delete_by_source(source)

    # ========== 综合方法 ==========

    async def retrieve_all(
            self,
            query: str,
            short_term_n: int = 10,
            long_term_top_k: int = 5,
            include_working: bool = True
    ) -> Dict[str, Any]:
        """
        检索所有类型的记忆

        Args:
            query: 查询文本（用于长期记忆检索）
            short_term_n: 短期记忆返回数量
            long_term_top_k: 长期记忆返回数量
            include_working: 是否包含工作记忆

        Returns:
            Dict: 包含所有类型记忆的结果
        """
        # 短期记忆
        short_term_messages = self.short_term.get_recent(short_term_n)

        # 长期记忆（自动按会话过滤）
        long_term_items = await self.retrieve_long_term(query, top_k=long_term_top_k)

        # 工作记忆
        working_memory = self.get_all_working() if include_working else {}

        return {
            "short_term": short_term_messages,
            "long_term": [item.dict() for item in long_term_items],
            "working": working_memory,
            "context": {
                "short_term_context": self.get_short_term_context(short_term_n),
                "working_summary": self.get_working_summary() if include_working else ""
            }
        }

    def clear_session(self, session_id: Optional[str] = None):
        """
        清空指定会话的记忆（不清空会话切换）

        Args:
            session_id: 会话ID，默认清空当前会话
        """
        target_session = session_id or self._current_session_id
        if not target_session:
            return

        # 清空短期记忆
        if target_session in self._short_term_memories:
            self._short_term_memories[target_session].clear()

        # 清空工作记忆
        if target_session in self._working_memories:
            self._working_memories[target_session].clear()

        logger.info(f"清空会话记忆: {target_session}")

    def delete_session(self, session_id: str):
        """
        完全删除会话的所有记忆（包括长期记忆）

        Args:
            session_id: 会话ID
        """
        # 删除短期记忆
        if session_id in self._short_term_memories:
            del self._short_term_memories[session_id]

        # 删除工作记忆
        if session_id in self._working_memories:
            del self._working_memories[session_id]

        logger.info(f"删除会话: {session_id}")

    def get_session_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """获取指定会话的统计信息"""
        target_session = session_id or self._current_session_id
        if not target_session:
            return {"error": "未指定会话"}

        short_term = self._short_term_memories.get(target_session)
        working = self._working_memories.get(target_session)

        return {
            "session_id": target_session,
            "short_term_count": short_term.get_size() if short_term else 0,
            "working_count": len(working.get_all()) if working else 0,
        }

    def get_stats(self) -> MemoryStats:
        """获取当前会话的记忆统计信息"""
        short_count = self.short_term.get_size()
        working_count = len(self.working.get_all())
        long_stats = self.long_term.get_stats(self._current_session_id)
        long_count = long_stats.get("num_entities", 0) if long_stats.get("available") else 0

        return MemoryStats(
            short_term_count=short_count,
            long_term_count=long_count,
            working_count=working_count,
            total_count=short_count + long_count + working_count
        )

    def get_all_sessions(self) -> List[str]:
        """获取所有活跃会话ID"""
        return list(self._short_term_memories.keys())

    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        return session_id in self._short_term_memories


# 全局单例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(
        vector_store=None,
        short_term_config: Optional[ShortTermConfig] = None,
        working_config: Optional[WorkingMemoryConfig] = None,
        long_term_config: Optional[LongTermConfig] = None
) -> MemoryManager:
    """
    获取全局记忆管理器单例

    Args:
        vector_store: 向量存储实例（首次创建时需要）
        short_term_config: 短期记忆配置
        working_config: 工作记忆配置
        long_term_config: 长期记忆配置

    Returns:
        MemoryManager: 记忆管理器实例
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(
            short_term_config=short_term_config,
            working_config=working_config,
            long_term_config=long_term_config,
            vector_store=vector_store
        )
    return _memory_manager