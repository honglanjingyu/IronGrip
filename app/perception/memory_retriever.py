# app/perception/memory_retriever.py - 修复长期记忆检索

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import deque
from loguru import logger

from .models import MemoryItem, MemoryType
from .config import retrieval_config

# 导入记忆模块
from app.memory import (
    ShortTermMemory as CoreShortTermMemory,
    WorkingMemory as CoreWorkingMemory,
    LongTermMemory as CoreLongTermMemory,
)
from app.memory.models import ShortTermConfig, WorkingMemoryConfig, LongTermConfig


class ShortTermMemory:
    """短期记忆 - 适配器，委托给核心记忆模块"""

    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._core = CoreShortTermMemory(ShortTermConfig(max_size=max_size))
        logger.info(f"ShortTermMemory 适配器初始化: max_size={max_size}")

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息"""
        if role == "user":
            self._core.add_user_message(content, metadata)
        elif role == "assistant":
            self._core.add_assistant_message(content, metadata)
        elif role == "system":
            self._core.add_system_message(content, metadata)
        else:
            self._core._add_message(role, content, metadata)

    def get_recent(self, n: int = 10) -> List[Dict]:
        """获取最近N条消息"""
        messages = self._core.get_recent(n)
        return [
            {
                "id": msg.get("id", ""),
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "metadata": msg.get("metadata", {}),
                "timestamp": msg.get("timestamp", "")
            }
            for msg in messages
        ]

    def get_all(self) -> List[Dict]:
        messages = self._core.get_all()
        return [
            {
                "id": msg.get("id", ""),
                "role": msg.get("role", ""),
                "content": msg.get("content", ""),
                "metadata": msg.get("metadata", {}),
                "timestamp": msg.get("timestamp", "")
            }
            for msg in messages
        ]

    def clear(self):
        self._core.clear()
        logger.info("短期记忆已清空")

    @property
    def messages(self):
        """兼容性属性，返回消息列表"""
        return self.get_all()


class LongTermMemory:
    """长期记忆 - 适配器，委托给核心记忆模块"""

    def __init__(self, vector_store_manager=None):
        self.vector_store = vector_store_manager
        if vector_store_manager:
            self._core = CoreLongTermMemory(vector_store=vector_store_manager)
        else:
            self._core = None
        logger.info("LongTermMemory 适配器初始化完成")

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """从知识库检索相关记忆"""
        if self._core is None:
            logger.warning("长期记忆未配置")
            return []

        top_k = top_k or retrieval_config.SIMILARITY_TOP_K
        results = await self._core.retrieve(
            query,
            top_k=top_k,
            enable_rerank=enable_rerank
        )

        # 转换为感知模块的 MemoryItem 格式
        return [
            MemoryItem(
                id=item.id,
                type=MemoryType.LONG_TERM,
                content=item.content,
                metadata=item.metadata,
                score=item.score,
                timestamp=item.timestamp
            )
            for item in results
        ]

    async def retrieve_with_score(
        self,
        query: str,
        top_k: Optional[int] = None
    ) -> List[tuple]:
        """从知识库检索相关记忆（带原始分数）"""
        if self._core is None:
            return []

        top_k = top_k or retrieval_config.SIMILARITY_TOP_K
        return await self._core.retrieve(query, top_k=top_k)

    async def retrieve_hybrid(
        self,
        query: str,
        top_k: Optional[int] = None,
        vector_weight: Optional[float] = None,
        keyword_weight: Optional[float] = None,
        enable_rerank: bool = True
    ) -> List[MemoryItem]:
        """混合检索"""
        if self._core is None:
            return []

        results = await self._core.retrieve_hybrid(
            query,
            top_k=top_k,
            enable_rerank=enable_rerank
        )
        return [
            MemoryItem(
                id=item.id,
                type=MemoryType.LONG_TERM,
                content=item.content,
                metadata=item.metadata,
                score=item.score,
                timestamp=item.timestamp
            )
            for item in results
        ]

    async def add_knowledge(self, content: str, metadata: Optional[Dict] = None):
        """添加知识到长期记忆"""
        if self._core:
            await self._core.add_knowledge(content, metadata)


class WorkingMemory:
    """工作记忆 - 适配器，委托给核心记忆模块"""

    def __init__(self):
        self._core = CoreWorkingMemory(WorkingMemoryConfig())
        logger.info("WorkingMemory 适配器初始化完成")

    def set(self, key: str, value: Any):
        self._core.set(key, value)

    def get(self, key: str, default=None) -> Any:
        return self._core.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        return self._core.get_all()

    def clear(self):
        self._core.clear()

    def get_summary(self) -> str:
        return self._core.get_summary()


class MemoryRetriever:
    """记忆检索器 - 统一管理短期、长期和工作记忆"""

    def __init__(self, vector_store_manager=None):
        self.short_term = ShortTermMemory(max_size=20)
        self.long_term = LongTermMemory(vector_store_manager)
        self.working = WorkingMemory()
        logger.info("MemoryRetriever 初始化完成")

    async def retrieve_all(
        self,
        query: str,
        session_id: str,
        include_long_term: bool = True,
        top_k: Optional[int] = None
    ) -> tuple[List[MemoryItem], List[MemoryItem], Dict[str, Any]]:
        """检索所有类型的记忆"""
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
            f"短期={len(short_term_items)}, 长期={len(long_term_items)}"
        )
        return short_term_items, long_term_items, working_memory

    def add_to_short_term(self, user_input: str, assistant_output: str):
        self.short_term.add_message("user", user_input)
        self.short_term.add_message("assistant", assistant_output)

    def add_to_working(self, key: str, value: Any):
        self.working.set(key, value)

    async def add_to_long_term(self, content: str, metadata: Optional[Dict] = None):
        await self.long_term.add_knowledge(content, metadata)

    def clear_session(self):
        self.short_term.clear()
        self.working.clear()
        logger.info("会话记忆已清空")